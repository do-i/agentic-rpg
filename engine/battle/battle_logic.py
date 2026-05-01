# engine/battle/battle_logic.py
#
# Battle logic — victory/defeat, party sync, flee, plus re-exports for the
# action_resolver and turn_advance helpers that used to live here. Existing
# imports (battle_scene, battle_enemy_logic, tests) keep working unchanged.

from __future__ import annotations

from engine.battle.action_resolver import (  # re-exports
    SIDE_EFFECT_KINDS,
    resolve_action,
    roll_and_apply_side_effects,
)
from engine.battle.battle_floats import (  # re-exports
    C_DEFEND, C_DMG_MAGIC, C_DMG_PHYS, C_HEAL,
    enemy_rect_size, float_pos,
)
from engine.battle.battle_rewards import RewardCalculator
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant
from engine.battle.turn_advance import (  # re-exports
    advance_to_next_turn,
    skip_if_incapacitated,
    tick_active_end_of_turn,
)
from engine.encounter.encounter_manager import EncounterManager
from engine.util.pseudo_random import PseudoRandom


__all__ = [
    # Re-exports from action_resolver
    "SIDE_EFFECT_KINDS",
    "resolve_action",
    "roll_and_apply_side_effects",
    # Re-exports from battle_floats
    "C_DEFEND", "C_DMG_MAGIC", "C_DMG_PHYS", "C_HEAL",
    "enemy_rect_size", "float_pos",
    # Re-exports from turn_advance
    "advance_to_next_turn", "skip_if_incapacitated", "tick_active_end_of_turn",
    # Defined here
    "FLEE_BASE_CHANCE", "FLEE_ROGUE_DEX_BONUS",
    "attempt_flee", "check_result",
    "handle_defeat", "handle_victory", "sync_party_state",
]


def handle_victory(
    state: BattleState,
    holder,
    boss_flag: str,
    reward_calc: RewardCalculator,
):
    """Process victory: set flags, calculate rewards, sync party. Returns rewards."""
    state.phase = BattlePhase.POST_BATTLE
    game_state = holder.get()

    if boss_flag:
        game_state.flags.add_flag(boss_flag)

    rewards = reward_calc.calculate(
        enemies=state.enemies,
        party=game_state.party,
        boss_flag=boss_flag,
    )

    sync_party_state(state, game_state.party)
    EncounterManager.add_mc_drops(game_state.repository, rewards.loot.mc_drops)
    for item in rewards.loot.item_drops:
        entry = game_state.repository.add_item(item["id"], item.get("qty", 1))
        entry.is_loot = True
    return rewards


def handle_defeat(state: BattleState) -> None:
    """Mark the battle as game over."""
    state.phase = BattlePhase.GAME_OVER


def sync_party_state(state: BattleState, party) -> None:
    """Write surviving HP/MP from Combatants back to MemberState."""
    combatant_map = {c.id: c for c in state.party}
    for member in party.members:
        c = combatant_map.get(member.id)
        if c is None:
            continue
        member.hp = c.hp
        member.mp = c.mp
        if c.is_ko:
            member.hp = 0


def check_result(state: BattleState) -> str:
    """Check for victory/defeat after an action resolves.
    Returns "victory", "defeat", or "continue".
    """
    if state.enemies_wiped:
        return "victory"
    if state.party_wiped:
        return "defeat"
    return "continue"


# ── Flee ─────────────────────────────────────────────────────
# Fallback defaults — authoritative values live in the scenario balance YAML
# and flow in through the `balance` parameter.
FLEE_BASE_CHANCE = 0.30
FLEE_ROGUE_DEX_BONUS = 0.02


def attempt_flee(state: BattleState, holder, rng: PseudoRandom,
                 balance=None) -> tuple[bool, str]:
    """Attempt to flee from battle.

    Returns (success, message).
    Boss battles always block flee.
    Formula: base_chance + dex_bonus per Rogue DEX in the party.
    Values sourced from balance.yaml when `balance` is supplied.
    """
    if any(e.boss for e in state.enemies):
        return False, "Can't escape from a boss!"

    base_chance     = balance.flee_base_chance     if balance else FLEE_BASE_CHANCE
    rogue_dex_bonus = balance.flee_rogue_dex_bonus if balance else FLEE_ROGUE_DEX_BONUS

    chance = base_chance
    party = holder.get().party
    for member in party.members:
        if member.class_name.lower() == "rogue":
            chance += rogue_dex_bonus * member.dex

    chance = min(chance, 1.0)

    if rng.random() < chance:
        return True, "Got away safely!"
    return False, "Couldn't escape!"
