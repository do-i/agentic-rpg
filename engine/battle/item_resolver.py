# engine/battle/item_resolver.py
#
# In-battle item-use resolution. Used by action_resolver.

from __future__ import annotations

from engine.battle.battle_floats import C_HEAL, float_pos
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant


def resolve_item(
    state: BattleState,
    source: Combatant,
    target: Combatant,
    action: dict,
    screen_width: int,
    *,
    effect_handler,
) -> list[str]:
    item_id = action.get("data", {}).get("id", "")
    item_label = item_id.replace("_", " ").title()
    defn = effect_handler.get_def(item_id) if effect_handler else None
    if defn is None:
        # Fallback for unknown items.
        actual = target.apply_heal(100)
        state.add_float(str(actual), *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used item on {target.name}! Healed {actual} HP!"]

    defn_effect = defn.effect
    effect_handler.apply_to_target(defn, target)
    if defn_effect == "revive" and target.hp > 0:
        target.is_ko = False

    if defn_effect in ("restore_hp", "restore_mp", "restore_full"):
        amount_label = str(defn.amount) if defn.amount else "Full"
        state.add_float(amount_label, *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used {item_label} on {target.name}!"]
    if defn_effect == "revive":
        state.add_float("Revive", *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used {item_label}! {target.name} revived!"]
    if defn_effect == "cure":
        state.add_float("Cured", *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used {item_label} on {target.name}!"]
    state.add_float("Used", *float_pos(state, target, screen_width), C_HEAL)
    return [f"{source.name} used {item_label} on {target.name}!"]
