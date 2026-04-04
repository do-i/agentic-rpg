# tests/unit/core/scenes/test_battle_logic.py

import pytest
from unittest.mock import MagicMock, patch

from engine.core.battle.combatant import Combatant, StatusEffect
from engine.core.battle.battle_state import BattleState, BattlePhase
from engine.core.battle.battle_rewards import RewardCalculator
from engine.core.scenes.battle_logic import (
    resolve_action, resolve_enemy_turn, handle_victory, handle_defeat,
    check_result, advance_to_next_turn, sync_party_state,
    float_pos, enemy_rect_size, ENEMY_SIZES,
)


def make_combatant(name="Hero", hp=100, hp_max=100, mp=50, mp_max=50,
                   atk=20, def_=5, mres=10, dex=10, is_enemy=False,
                   boss=False, abilities=None) -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=hp, hp_max=hp_max, mp=mp, mp_max=mp_max,
        atk=atk, def_=def_, mres=mres, dex=dex,
        is_enemy=is_enemy, boss=boss,
        abilities=abilities or [],
    )


def make_battle_state(party=None, enemies=None) -> BattleState:
    party = party or [make_combatant("Hero")]
    enemies = enemies or [make_combatant("Goblin", is_enemy=True, atk=10, def_=3)]
    return BattleState(party=party, enemies=enemies)


# ── resolve_action ────────────────────────────────────────────

class TestResolveAction:
    def test_attack_deals_damage(self):
        hero = make_combatant("Hero", atk=20)
        goblin = make_combatant("Goblin", hp=50, hp_max=50, def_=5, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        state.pending_action = {"type": "attack", "source": hero, "targets": [goblin]}

        msg = resolve_action(state)

        assert goblin.hp == 35  # 50 - (20-5)
        assert "attacked" in msg
        assert state.pending_action is None

    def test_attack_damage_minimum_one(self):
        hero = make_combatant("Hero", atk=1)
        goblin = make_combatant("Goblin", hp=50, hp_max=50, def_=100, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        state.pending_action = {"type": "attack", "source": hero, "targets": [goblin]}

        resolve_action(state)

        assert goblin.hp == 49  # min 1 damage

    def test_heal_spell_restores_hp(self):
        hero = make_combatant("Hero", mp=30, mres=20)
        ally = make_combatant("Ally", hp=50, hp_max=100)
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        spell = {"name": "Heal", "type": "heal", "heal_coeff": 2.0, "mp_cost": 10,
                 "target": "single_ally"}
        state.pending_action = {
            "type": "spell", "data": spell, "source": hero, "targets": [ally],
        }

        msg = resolve_action(state)

        assert ally.hp == 90  # 50 + int(20 * 2.0)
        assert hero.mp == 20  # 30 - 10
        assert "healed" in msg

    def test_revive_spell(self):
        hero = make_combatant("Hero", mp=30, mres=10)
        dead = make_combatant("Dead", hp=0, hp_max=100)
        dead.is_ko = True
        state = make_battle_state([hero, dead], [make_combatant("Goblin", is_enemy=True)])
        spell = {"name": "Revive", "type": "heal", "revive_hp_pct": 0.5, "mp_cost": 15}
        state.pending_action = {
            "type": "spell", "data": spell, "source": hero, "targets": [dead],
        }

        msg = resolve_action(state)

        assert dead.hp == 50  # 100 * 0.5
        assert not dead.is_ko
        assert "revived" in msg.lower()

    def test_utility_spell_clears_status(self):
        hero = make_combatant("Hero", mp=20, mres=10)
        poisoned = make_combatant("Ally", hp=80, hp_max=100)
        poisoned.add_status(StatusEffect.POISON)
        state = make_battle_state([hero, poisoned], [make_combatant("Goblin", is_enemy=True)])
        spell = {"name": "Esuna", "type": "utility", "mp_cost": 5}
        state.pending_action = {
            "type": "spell", "data": spell, "source": hero, "targets": [poisoned],
        }

        msg = resolve_action(state)

        assert not poisoned.status_effects
        assert "cured" in msg.lower()

    def test_offensive_spell_deals_magic_damage(self):
        hero = make_combatant("Hero", mp=30, mres=15)
        goblin = make_combatant("Goblin", hp=50, hp_max=50, def_=3, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        spell = {"name": "Fire", "type": "spell", "spell_coeff": 2.0, "mp_cost": 8}
        state.pending_action = {
            "type": "spell", "data": spell, "source": hero, "targets": [goblin],
        }

        resolve_action(state)

        # dmg = max(1, int(15 * 2.0) - 3) = 27
        assert goblin.hp == 23

    def test_item_heals_100(self):
        hero = make_combatant("Hero")
        ally = make_combatant("Ally", hp=50, hp_max=200)
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "potion"}, "source": hero, "targets": [ally],
        }

        msg = resolve_action(state)

        assert ally.hp == 150
        assert "Healed" in msg

    def test_no_pending_action_returns_empty(self):
        state = make_battle_state()
        state.pending_action = None

        msg = resolve_action(state)

        assert msg == ""

    def test_buff_spell(self):
        hero = make_combatant("Hero", mp=30, mres=10)
        ally = make_combatant("Ally")
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        spell = {"name": "Protect", "type": "buff", "mp_cost": 5}
        state.pending_action = {
            "type": "spell", "data": spell, "source": hero, "targets": [ally],
        }

        msg = resolve_action(state)

        assert "Protect" in msg

    def test_debuff_spell(self):
        hero = make_combatant("Hero", mp=30, mres=10)
        goblin = make_combatant("Goblin", hp=50, hp_max=50, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        spell = {"name": "Slow", "type": "debuff", "mp_cost": 5}
        state.pending_action = {
            "type": "spell", "data": spell, "source": hero, "targets": [goblin],
        }

        msg = resolve_action(state)

        assert "Slow" in msg


# ── resolve_enemy_turn ────────────────────────────────────────

class TestResolveEnemyTurn:
    def test_enemy_attacks_party_member(self):
        hero = make_combatant("Hero", hp=100, hp_max=100, def_=5)
        goblin = make_combatant("Goblin", atk=15, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        state.build_turn_order()
        # force goblin active
        state.active_index = state.turn_order.index(goblin)

        msg = resolve_enemy_turn(state)

        assert hero.hp == 90  # 100 - (15-5)
        assert "attacked" in msg

    def test_non_enemy_returns_empty(self):
        hero = make_combatant("Hero")
        state = make_battle_state([hero], [make_combatant("Goblin", is_enemy=True)])
        state.build_turn_order()
        state.active_index = state.turn_order.index(hero)

        msg = resolve_enemy_turn(state)

        assert msg == ""

    def test_no_alive_targets_returns_empty(self):
        hero = make_combatant("Hero", hp=0)
        hero.is_ko = True
        goblin = make_combatant("Goblin", atk=10, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        state.build_turn_order()
        state.active_index = state.turn_order.index(goblin)

        msg = resolve_enemy_turn(state)

        assert msg == ""


# ── check_result ──────────────────────────────────────────────

class TestCheckResult:
    def test_victory_when_enemies_wiped(self):
        goblin = make_combatant("Goblin", hp=0, is_enemy=True)
        goblin.is_ko = True
        state = make_battle_state([make_combatant("Hero")], [goblin])

        assert check_result(state) == "victory"

    def test_defeat_when_party_wiped(self):
        hero = make_combatant("Hero", hp=0)
        hero.is_ko = True
        state = make_battle_state([hero], [make_combatant("Goblin", is_enemy=True)])

        assert check_result(state) == "defeat"

    def test_continue_when_both_alive(self):
        state = make_battle_state()

        assert check_result(state) == "continue"


# ── advance_to_next_turn ─────────────────────────────────────

class TestAdvanceToNextTurn:
    def test_switches_to_enemy_turn(self):
        hero = make_combatant("Hero", dex=5)
        goblin = make_combatant("Goblin", dex=10, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        state.build_turn_order()
        # goblin goes first (higher dex), advance should go to hero
        state.phase = BattlePhase.RESOLVE

        advance_to_next_turn(state)

        assert state.phase == BattlePhase.PLAYER_TURN

    def test_switches_to_player_turn(self):
        hero = make_combatant("Hero", dex=20)
        goblin = make_combatant("Goblin", dex=5, is_enemy=True)
        state = make_battle_state([hero], [goblin])
        state.build_turn_order()
        # hero goes first (higher dex), advance should go to goblin

        advance_to_next_turn(state)

        assert state.phase == BattlePhase.ENEMY_TURN


# ── handle_victory ────────────────────────────────────────────

class TestHandleVictory:
    def test_sets_boss_flag(self):
        hero = make_combatant("Hero")
        goblin = make_combatant("Goblin", hp=0, is_enemy=True, boss=True)
        goblin.is_ko = True
        state = make_battle_state([hero], [goblin])

        holder = MagicMock()
        game_state = MagicMock()
        game_state.party.members = []
        holder.get.return_value = game_state

        reward_calc = MagicMock(spec=RewardCalculator)
        reward_calc.calculate.return_value = MagicMock(loot=MagicMock(mc_drops=[]))

        handle_victory(state, holder, "boss_defeated", reward_calc)

        game_state.flags.add_flag.assert_called_with("boss_defeated")
        assert state.phase == BattlePhase.POST_BATTLE

    def test_no_boss_flag_when_empty(self):
        state = make_battle_state()

        holder = MagicMock()
        game_state = MagicMock()
        game_state.party.members = []
        holder.get.return_value = game_state

        reward_calc = MagicMock(spec=RewardCalculator)
        reward_calc.calculate.return_value = MagicMock(loot=MagicMock(mc_drops=[]))

        handle_victory(state, holder, "", reward_calc)

        game_state.flags.add_flag.assert_not_called()


# ── handle_defeat ─────────────────────────────────────────────

class TestHandleDefeat:
    def test_sets_game_over_phase(self):
        state = make_battle_state()

        handle_defeat(state)

        assert state.phase == BattlePhase.GAME_OVER


# ── sync_party_state ──────────────────────────────────────────

class TestSyncPartyState:
    def test_syncs_hp_mp(self):
        hero_c = make_combatant("Hero", hp=42, mp=13)
        state = make_battle_state([hero_c])

        member = MagicMock()
        member.id = "hero"
        party = MagicMock()
        party.members = [member]

        sync_party_state(state, party)

        assert member.hp == 42
        assert member.mp == 13

    def test_ko_sets_hp_zero(self):
        hero_c = make_combatant("Hero", hp=0)
        hero_c.is_ko = True
        state = make_battle_state([hero_c])

        member = MagicMock()
        member.id = "hero"
        party = MagicMock()
        party.members = [member]

        sync_party_state(state, party)

        assert member.hp == 0

    def test_unknown_member_skipped(self):
        hero_c = make_combatant("Hero", hp=50)
        state = make_battle_state([hero_c])

        member = MagicMock()
        member.id = "unknown"
        party = MagicMock()
        party.members = [member]

        # should not raise
        sync_party_state(state, party)


# ── enemy_rect_size ───────────────────────────────────────────

class TestEnemyRectSize:
    def test_boss_returns_large(self):
        c = make_combatant("Boss", boss=True, is_enemy=True)
        assert enemy_rect_size(c) == ENEMY_SIZES["large"]

    def test_non_boss_returns_based_on_name_length(self):
        c = make_combatant("Goblin", is_enemy=True)
        size = enemy_rect_size(c)
        assert size in (ENEMY_SIZES["medium"], ENEMY_SIZES["small"])


# ── float_pos ─────────────────────────────────────────────────

class TestFloatPos:
    def test_enemy_float_pos(self):
        goblin = make_combatant("Goblin", is_enemy=True)
        state = make_battle_state([make_combatant("Hero")], [goblin])

        x, y = float_pos(state, goblin)

        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_party_float_pos(self):
        hero = make_combatant("Hero")
        state = make_battle_state([hero], [make_combatant("Goblin", is_enemy=True)])

        x, y = float_pos(state, hero)

        assert isinstance(x, int)
        assert isinstance(y, int)
