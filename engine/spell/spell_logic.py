# engine/spell/spell_logic.py
#
# Learned-spell lookup for the Field Menu Spells screen.
# The battle-side ability filter is implemented separately in
# encounter_manager._load_class_abilities (it gates enemy/party battle
# menus). This module serves the field menu.

from __future__ import annotations

from pathlib import Path
import yaml

from engine.party.member_state import MemberState


# Ability types that are considered spells / castable actions.
CASTING_TYPES = {"spell", "heal", "buff", "debuff", "utility"}

# Spell types that can be cast from the field menu (outside battle).
FIELD_CASTABLE_TYPES = {"heal", "utility", "buff"}

# Target types that mean "enemy only" — excluded from field casting even
# if a spell's top-level type would otherwise allow it.
BATTLE_ONLY_TARGETS = {"single_enemy", "all_enemies", "group_enemies"}


def _load_class_abilities(classes_dir: Path, class_name: str) -> list[dict]:
    path = classes_dir / f"{class_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Class YAML not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("abilities", [])


def learned_spells(
    member: MemberState, classes_dir: Path, flags: set[str],
) -> list[dict]:
    """All spells the member currently knows.

    Filtered by: ability type is a casting type, unlock_level <= member.level,
    and if the ability has an `unlock_flag`, it must be present in `flags`.
    Order matches the class YAML.
    """
    result = []
    for ab in _load_class_abilities(classes_dir, member.class_name):
        if ab.get("type") not in CASTING_TYPES:
            continue
        if ab["unlock_level"] > member.level:
            continue
        unlock_flag = ab.get("unlock_flag")
        if unlock_flag and unlock_flag not in flags:
            continue
        result.append(ab)
    return result


def is_field_castable(spell: dict) -> bool:
    """True if the spell can be cast from the field menu (outside battle)."""
    if spell.get("type") not in FIELD_CASTABLE_TYPES:
        return False
    target = spell.get("target")
    if target in BATTLE_ONLY_TARGETS:
        return False
    return True
