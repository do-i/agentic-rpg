# engine/battle/turn_advance.py
#
# End-of-turn ticking and turn advancement helpers for the battle scene.
# Action resolution lives in action_resolver.py; victory/defeat in
# battle_logic.py. These three helpers were grouped here per §4.5 since
# they form one logical phase of each turn boundary.

from __future__ import annotations

from engine.battle.battle_floats import C_DMG_MAGIC, float_pos
from engine.battle.battle_state import BattleState, BattlePhase


def tick_active_end_of_turn(state: BattleState, screen_width: int) -> str:
    """Tick end-of-turn statuses on the currently active combatant.

    Applies BURN DOT, decrements durations, removes expired statuses. Returns
    a message describing DOT damage (empty if none).
    """
    active = state.active
    if active is None or not active.is_alive:
        return ""
    dot = active.tick_end_of_turn()
    if dot <= 0:
        return ""
    state.add_float(str(dot), *float_pos(state, active, screen_width), C_DMG_MAGIC)
    return f"{active.name} takes {dot} burn damage!"


def advance_to_next_turn(state: BattleState) -> None:
    """Advance to the next turn and set the phase accordingly."""
    state.advance_turn()
    active = state.active
    if active:
        active.defending = False
    if active and active.is_enemy:
        state.phase = BattlePhase.ENEMY_TURN
    else:
        state.phase = BattlePhase.PLAYER_TURN


def skip_if_incapacitated(state: BattleState) -> str:
    """If the active combatant has a skip-turn status, consume the turn.

    Ticks their end-of-turn (so the stun/freeze duration decreases), advances
    the turn, and returns a message. Returns "" when the active can act.
    """
    active = state.active
    if active is None or not active.is_alive:
        return ""
    reason = active.skip_turn_reason
    if reason is None:
        return ""
    name = reason.name.lower()
    active.tick_end_of_turn()
    msg = f"{active.name} can't move ({name})!"
    advance_to_next_turn(state)
    return msg
