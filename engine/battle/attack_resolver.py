# engine/battle/attack_resolver.py
#
# Basic-attack resolution. Used by action_resolver.

from __future__ import annotations

from engine.battle.battle_floats import C_DMG_PHYS, float_pos
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.util.pseudo_random import PseudoRandom


def resolve_attack(
    state: BattleState,
    source: Combatant,
    target: Combatant,
    screen_width: int,
    *,
    rng: PseudoRandom | None,
    fx: BattleFx | None,
) -> list[str]:
    src_atk = source.effective_atk if source else 0
    dmg = max(1, src_atk - target.effective_def)
    # Basic attack is melee; back-row attacker deals halved damage.
    if source and source.row == "back":
        dmg = max(1, dmg // 2)
    # Back-row defender takes halved physical.
    if target.row == "back":
        dmg = max(1, dmg // 2)
    actual = target.apply_damage(dmg, rng)
    state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_PHYS)
    if fx:
        fx.hit(target)
    return [f"{source.name} attacked {target.name} for {actual} damage!"]
