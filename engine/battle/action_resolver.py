# engine/battle/action_resolver.py
#
# Per-action dispatch for the battle scene. The scene's `do_resolve`
# pipes pending_action through `resolve_action` here; this module owns the
# attack/spell/item dispatch and MP-cost deduction. Per-kind resolution
# lives in attack_resolver / spell_resolver / item_resolver. Turn ticks live
# in turn_advance.py; victory/defeat in battle_logic.py.

from __future__ import annotations

from engine.battle.attack_resolver import resolve_attack
from engine.battle.battle_floats import C_DEFEND, float_pos
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_state import BattleState
from engine.battle.item_resolver import resolve_item
from engine.battle.spell_resolver import (
    SIDE_EFFECT_KINDS,
    resolve_spell,
    roll_and_apply_side_effects,
)
from engine.util.pseudo_random import PseudoRandom

__all__ = [
    "SIDE_EFFECT_KINDS",
    "resolve_action",
    "roll_and_apply_side_effects",
]


def resolve_action(state: BattleState, screen_width: int,
                   effect_handler=None, repository=None,
                   rng: PseudoRandom | None = None,
                   fx: BattleFx | None = None) -> str:
    """Execute the pending action. Returns the message to display."""
    action = state.pending_action
    if not action:
        return ""
    source = action.get("source")
    targets = action.get("targets", [])
    atype = action.get("type", "attack")
    msg_parts: list[str] = []

    if atype == "defend":
        source.defending = True
        state.add_float("Defend", *float_pos(state, source, screen_width), C_DEFEND)
        state.pending_action = None
        return f"{source.name} is defending!"

    # MP for spells is deducted once up front (not per target). Combatant is
    # a dataclass with field-level equality, so iterating "deduct once on the
    # first target" via target == targets[0] is unsafe — an AOE buff that
    # doesn't mutate compared fields would leave every iteration equal.
    if atype == "spell" and source and targets:
        ab = action.get("data", {})
        source.mp = max(0, source.mp - ab["mp_cost"])

    for target in targets:
        if atype == "attack":
            msg_parts.extend(resolve_attack(
                state, source, target, screen_width, rng=rng, fx=fx,
            ))
        elif atype == "spell":
            msg_parts.extend(resolve_spell(
                state, source, target, action, screen_width, rng=rng, fx=fx,
            ))
        elif atype == "item":
            msg_parts.extend(resolve_item(
                state, source, target, action, screen_width,
                effect_handler=effect_handler,
            ))

    # Decrement item qty after all targets resolved.
    if atype == "item" and effect_handler and repository:
        item_id = action.get("data", {}).get("id", "")
        defn = effect_handler.get_def(item_id)
        if defn and defn.consumable:
            repository.remove_item(item_id, 1)

    state.pending_action = None
    return msg_parts[0] if msg_parts else ""
