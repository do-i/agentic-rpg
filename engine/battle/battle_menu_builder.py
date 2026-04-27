# engine/battle/battle_menu_builder.py
#
# Pure builders for the battle command sub-menus (Spell, Item).
# No pygame, no state mutation — given an active combatant or repository,
# return the list[dict] the renderer/input controller consume.

from __future__ import annotations

from engine.battle.combatant import Combatant


# Maps an item def's `target` field to the battle's target-pool keyword.
# Item defs use field-style targets (single_alive/single_ko/all_alive)
# while battle resolution uses single_ally / single_ko / all_allies.
TARGET_MAP = {
    "single_alive": "single_ally",
    "single_ko":    "single_ko",
    "all_alive":    "all_allies",
}


SPELL_TYPES = ("spell", "heal", "buff", "debuff", "utility")


def build_spell_menu(active: Combatant) -> list[dict]:
    """Build sub-menu rows from the active combatant's learned abilities.

    Disabled rows are still listed so the player can see costs they can't
    yet afford; the input controller refuses to confirm a disabled row.
    """
    items: list[dict] = []
    for ab in active.abilities:
        if ab.get("type") not in SPELL_TYPES:
            continue
        cost = ab["mp_cost"]
        items.append({
            "label":    ab["name"],
            "mp_cost":  cost,
            "data":     ab,
            "disabled": active.mp < cost,
        })
    return items


def build_item_menu(repo, effect_handler) -> list[dict]:
    """Build sub-menu rows from inventory items that have an in-battle effect.

    Items without a registered effect handler entry are skipped (they can
    only be used on the field). Falls back to single_ally targeting when
    the def's target field doesn't appear in TARGET_MAP.
    """
    items: list[dict] = []
    for entry in repo.items:
        defn = effect_handler.get_def(entry.id) if effect_handler else None
        if not defn:
            continue
        target = TARGET_MAP.get(defn.target, "single_ally")
        label = entry.id.replace("_", " ").title()
        items.append({
            "label":    label,
            "qty":      entry.qty,
            "data":     {"id": entry.id, "target": target},
            "disabled": False,
        })
    return items
