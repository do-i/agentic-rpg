# engine/service/status_logic.py
#
# Status scene logic — spell filtering, validation, application.
# Extracted from status_scene.py to separate game logic from rendering.

from __future__ import annotations

from pathlib import Path
import yaml

from engine.party.member_state import MemberState

# field-usable spell types (no offensive spells on world map)
FIELD_SPELL_TYPES = {"heal", "utility", "buff"}


def load_class_data(classes_dir: Path, class_name: str) -> dict:
    path = classes_dir / f"{class_name}.yaml"
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)


def field_spells(member: MemberState, scenario_path: str) -> list[dict]:
    """Load available field-usable spells for this member."""
    classes_dir = Path(scenario_path) / "data" / "classes"
    class_data = load_class_data(classes_dir, member.class_name)
    abilities = class_data.get("abilities", [])
    result = []
    for ab in abilities:
        if ab.get("type") not in FIELD_SPELL_TYPES:
            continue
        if ab.get("unlock_level", 1) > member.level:
            continue
        result.append(ab)
    return result


def valid_targets(spell: dict, members: list[MemberState]) -> list[MemberState]:
    """Return valid targets for the given spell."""
    target = spell.get("target", "single_ally")
    if target == "single_ko":
        return [m for m in members if m.hp <= 0]
    if spell.get("revive_hp_pct"):
        return [m for m in members if m.hp <= 0]
    return [m for m in members if m.hp > 0]


def apply_spell(spell: dict, caster: MemberState, target: MemberState) -> str:
    """Apply spell effect. Returns result message."""
    caster.mp = max(0, caster.mp - spell.get("mp_cost", 0))
    spell_type = spell.get("type")

    if spell_type == "heal":
        if spell.get("revive_hp_pct"):
            pct = spell["revive_hp_pct"]
            target.hp = max(1, int(target.hp_max * pct))
            return f"{target.name} revived!"
        coeff = spell.get("heal_coeff", 1.0)
        amount = int(caster.int_ * coeff)
        before = target.hp
        target.hp = min(target.hp_max, target.hp + amount)
        healed = target.hp - before
        return f"{target.name} healed {healed} HP!"

    if spell_type == "utility":
        return f"{target.name} cured!"

    if spell_type == "buff":
        return f"{spell['name']} cast!"

    return f"{spell['name']} used!"


def apply_spell_all(spell: dict, caster: MemberState, members: list[MemberState]) -> str:
    """Apply AoE heal to all alive members."""
    caster.mp = max(0, caster.mp - spell.get("mp_cost", 0))
    coeff = spell.get("heal_coeff", 1.0)
    amount = int(caster.int_ * coeff)
    total = 0
    for m in members:
        if m.hp <= 0:
            continue
        before = m.hp
        m.hp = min(m.hp_max, m.hp + amount)
        total += m.hp - before
    return f"Party healed {total} HP!"
