# tests/unit/core/scenes/test_battle_logic.py

import pytest
from unittest.mock import MagicMock, patch

from engine.core.battle.combatant import Combatant, StatusEffect
from engine.core.battle.battle_state import BattleState, BattlePhase
from engine.core.battle.battle_rewards import RewardCalculator
from engine.core.item.item_effect_handler import ItemEffectHandler, FieldItemDef
from engine.core.state.repository_state import RepositoryState
from engine.core.scenes.battle_logic import (
    resolve_action, resolve_enemy_turn, handle_victory, handle_defeat,
    check_result, advance_to_next_turn, sync_party_state,
    float_pos, enemy_rect_size, ENEMY_SIZES,
    attempt_flee, FLEE_BASE_CHANCE, FLEE_ROGUE_DEX_BONUS,
    pick_enemy_action, resolve_targeting,
    _check_condition, _weighted_pick_move,
)


def make_combatant(name="Hero", hp=100, hp_max=100, mp=50, mp_max=50,
                   atk=20, def_=5, mres=10, dex=10, is_enemy=False,
                   boss=False, abilities=None, ai_data=None) -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=hp, hp_max=hp_max, mp=mp, mp_max=mp_max,
        atk=atk, def_=def_, mres=mres, dex=dex,
        is_enemy=is_enemy, boss=boss,
        abilities=abilities or [],
        ai_data=ai_data or {},
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

    def test_item_fallback_heals_100_without_handler(self):
        """Without effect_handler, items fall back to hardcoded 100 HP heal."""
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


# ── Item resolution with effect_handler ──────────────────────

def _make_handler_with(*defs: FieldItemDef) -> ItemEffectHandler:
    """Create an ItemEffectHandler pre-loaded with given defs (no YAML)."""
    from pathlib import Path
    handler = ItemEffectHandler.__new__(ItemEffectHandler)
    handler._defs = {d.id: d for d in defs}
    return handler


class TestResolveActionItems:
    def test_potion_heals_correct_amount(self):
        handler = _make_handler_with(
            FieldItemDef(id="potion", effect="restore_hp", target="single_alive", amount=100),
        )
        repo = RepositoryState()
        repo.add_item("potion", 5)

        hero = make_combatant("Hero")
        ally = make_combatant("Ally", hp=50, hp_max=200)
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "potion"}, "source": hero, "targets": [ally],
        }

        msg = resolve_action(state, effect_handler=handler, repository=repo)

        assert ally.hp == 150
        assert "Potion" in msg
        assert repo.get_item("potion").qty == 4

    def test_hi_potion_heals_500(self):
        handler = _make_handler_with(
            FieldItemDef(id="hi_potion", effect="restore_hp", target="single_alive", amount=500),
        )
        repo = RepositoryState()
        repo.add_item("hi_potion", 3)

        hero = make_combatant("Hero")
        ally = make_combatant("Ally", hp=100, hp_max=300)
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "hi_potion"}, "source": hero, "targets": [ally],
        }

        resolve_action(state, effect_handler=handler, repository=repo)

        assert ally.hp == 300  # capped at max
        assert repo.get_item("hi_potion").qty == 2

    def test_antidote_cures_poison(self):
        handler = _make_handler_with(
            FieldItemDef(id="antidote", effect="cure", target="single_alive", cures=["poison"]),
        )
        repo = RepositoryState()
        repo.add_item("antidote", 2)

        hero = make_combatant("Hero")
        ally = make_combatant("Ally", hp=80, hp_max=100)
        ally.add_status(StatusEffect.POISON)
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "antidote"}, "source": hero, "targets": [ally],
        }

        msg = resolve_action(state, effect_handler=handler, repository=repo)

        assert not ally.has_status(StatusEffect.POISON)
        assert "Cured" in msg or "Antidote" in msg
        assert repo.get_item("antidote").qty == 1

    def test_revive_item_restores_ko(self):
        handler = _make_handler_with(
            FieldItemDef(id="life_crystal", effect="revive", target="single_ko", revive_hp_pct=1.0),
        )
        repo = RepositoryState()
        repo.add_item("life_crystal", 1)

        hero = make_combatant("Hero")
        dead = make_combatant("Dead", hp=0, hp_max=200)
        dead.is_ko = True
        state = make_battle_state([hero, dead], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "life_crystal"}, "source": hero, "targets": [dead],
        }

        msg = resolve_action(state, effect_handler=handler, repository=repo)

        assert dead.hp == 200  # 100% of hp_max
        assert not dead.is_ko
        assert "revived" in msg.lower()
        # consumable, qty was 1 → removed from repo
        assert repo.get_item("life_crystal") is None

    def test_non_consumable_item_not_decremented(self):
        handler = _make_handler_with(
            FieldItemDef(id="phoenix_wing", effect="revive", target="single_ko",
                         revive_hp_pct=0.30, consumable=False),
        )
        repo = RepositoryState()
        repo.add_item("phoenix_wing", 1)

        hero = make_combatant("Hero")
        dead = make_combatant("Dead", hp=0, hp_max=100)
        dead.is_ko = True
        state = make_battle_state([hero, dead], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "phoenix_wing"}, "source": hero, "targets": [dead],
        }

        resolve_action(state, effect_handler=handler, repository=repo)

        assert dead.hp == 30  # 30% of 100
        assert not dead.is_ko
        assert repo.get_item("phoenix_wing").qty == 1  # not decremented

    def test_ether_restores_mp(self):
        handler = _make_handler_with(
            FieldItemDef(id="ether", effect="restore_mp", target="single_alive", amount=50),
        )
        repo = RepositoryState()
        repo.add_item("ether", 2)

        hero = make_combatant("Hero", mp=10, mp_max=80)
        state = make_battle_state([hero], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "ether"}, "source": hero, "targets": [hero],
        }

        resolve_action(state, effect_handler=handler, repository=repo)

        assert hero.mp == 60
        assert repo.get_item("ether").qty == 1

    def test_elixir_restores_full(self):
        handler = _make_handler_with(
            FieldItemDef(id="elixir", effect="restore_full", target="single_alive"),
        )
        repo = RepositoryState()
        repo.add_item("elixir", 1)

        hero = make_combatant("Hero", hp=30, hp_max=100, mp=5, mp_max=50)
        state = make_battle_state([hero], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "elixir"}, "source": hero, "targets": [hero],
        }

        resolve_action(state, effect_handler=handler, repository=repo)

        assert hero.hp == 100
        assert hero.mp == 50
        assert repo.get_item("elixir") is None  # qty 1 → removed

    def test_last_item_removed_from_repo(self):
        handler = _make_handler_with(
            FieldItemDef(id="potion", effect="restore_hp", target="single_alive", amount=100),
        )
        repo = RepositoryState()
        repo.add_item("potion", 1)

        hero = make_combatant("Hero")
        ally = make_combatant("Ally", hp=50, hp_max=200)
        state = make_battle_state([hero, ally], [make_combatant("Goblin", is_enemy=True)])
        state.pending_action = {
            "type": "item", "data": {"id": "potion"}, "source": hero, "targets": [ally],
        }

        resolve_action(state, effect_handler=handler, repository=repo)

        assert repo.get_item("potion") is None
        assert len(repo.items) == 0


# ── attempt_flee ─────────────────────────────────────────────

def _make_holder_with_party(members):
    """Create a mock holder whose .get().party.members returns the given list."""
    holder = MagicMock()
    holder.get.return_value.party.members = members
    return holder


def _make_member(class_name="warrior", dex=10):
    m = MagicMock()
    m.class_name = class_name
    m.dex = dex
    return m


class TestAttemptFlee:
    def test_boss_always_blocks_flee(self):
        boss = make_combatant("Dragon", is_enemy=True, boss=True)
        state = make_battle_state([make_combatant("Hero")], [boss])
        holder = _make_holder_with_party([_make_member()])

        success, msg = attempt_flee(state, holder)

        assert not success
        assert "boss" in msg.lower()

    def test_success_when_roll_below_chance(self):
        state = make_battle_state()
        holder = _make_holder_with_party([_make_member("warrior", dex=10)])

        with patch("engine.core.scenes.battle_logic.random.random", return_value=0.0):
            success, msg = attempt_flee(state, holder)

        assert success
        assert "safely" in msg.lower()

    def test_failure_when_roll_above_chance(self):
        state = make_battle_state()
        holder = _make_holder_with_party([_make_member("warrior", dex=10)])

        with patch("engine.core.scenes.battle_logic.random.random", return_value=0.99):
            success, msg = attempt_flee(state, holder)

        assert not success
        assert "escape" in msg.lower()

    def test_rogue_dex_increases_chance(self):
        """With a rogue at DEX 20, chance = 0.30 + 0.02*20 = 0.70."""
        state = make_battle_state()
        holder = _make_holder_with_party([_make_member("rogue", dex=20)])

        # Roll at 0.65 — should succeed with rogue bonus (0.70) but fail without
        with patch("engine.core.scenes.battle_logic.random.random", return_value=0.65):
            success, _ = attempt_flee(state, holder)

        assert success

    def test_no_rogue_base_chance_only(self):
        """Without a rogue, chance is base 30%."""
        state = make_battle_state()
        holder = _make_holder_with_party([_make_member("warrior", dex=20)])

        # Roll at 0.35 — should fail with only base 30%
        with patch("engine.core.scenes.battle_logic.random.random", return_value=0.35):
            success, _ = attempt_flee(state, holder)

        assert not success

    def test_chance_capped_at_one(self):
        """Even with absurd DEX, chance never exceeds 1.0."""
        state = make_battle_state()
        holder = _make_holder_with_party([_make_member("rogue", dex=100)])

        with patch("engine.core.scenes.battle_logic.random.random", return_value=0.99):
            success, _ = attempt_flee(state, holder)

        assert success

    def test_multiple_rogues_stack(self):
        """Multiple rogues' DEX bonuses stack."""
        state = make_battle_state()
        holder = _make_holder_with_party([
            _make_member("rogue", dex=10),
            _make_member("rogue", dex=10),
        ])

        # chance = 0.30 + 0.02*10 + 0.02*10 = 0.70
        with patch("engine.core.scenes.battle_logic.random.random", return_value=0.65):
            success, _ = attempt_flee(state, holder)

        assert success


# ── pick_enemy_action ────────────────────────────────────────

class TestPickEnemyAction:
    def test_no_ai_data_returns_attack(self):
        enemy = make_combatant("Goblin", is_enemy=True)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        action = pick_enemy_action(enemy, state)

        assert action["action"] == "attack"

    def test_random_pattern_picks_from_moves(self):
        ai_data = {"ai": {"pattern": "random", "moves": [
            {"action": "attack", "weight": 70},
            {"action": "ability", "id": "scratch", "weight": 30},
        ]}}
        enemy = make_combatant("Goblin", is_enemy=True, ai_data=ai_data)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        with patch("engine.core.scenes.battle_logic.random.choices",
                   return_value=[ai_data["ai"]["moves"][1]]):
            action = pick_enemy_action(enemy, state)

        assert action["action"] == "ability"
        assert action["id"] == "scratch"

    def test_conditional_filters_by_hp(self):
        ai_data = {"ai": {"pattern": "conditional", "moves": [
            {"condition": {"hp_pct_below": 1.0}, "action": "attack", "weight": 50},
            {"condition": {"hp_pct_below": 0.5}, "action": "ability", "id": "enrage", "weight": 100},
        ]}}
        # enemy at full HP — only the first move is eligible
        enemy = make_combatant("Boss", hp=100, hp_max=100, is_enemy=True, ai_data=ai_data)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        action = pick_enemy_action(enemy, state)

        assert action["action"] == "attack"

    def test_conditional_unlocks_low_hp_move(self):
        ai_data = {"ai": {"pattern": "conditional", "moves": [
            {"condition": {"hp_pct_below": 1.0}, "action": "attack", "weight": 1},
            {"condition": {"hp_pct_below": 0.5}, "action": "ability", "id": "enrage", "weight": 999},
        ]}}
        # enemy at 30% HP — both moves eligible, enrage heavily weighted
        enemy = make_combatant("Boss", hp=30, hp_max=100, is_enemy=True, ai_data=ai_data)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        with patch("engine.core.scenes.battle_logic.random.choices",
                   return_value=[ai_data["ai"]["moves"][1]]):
            action = pick_enemy_action(enemy, state)

        assert action["id"] == "enrage"

    def test_conditional_turn_mod(self):
        ai_data = {"ai": {"pattern": "conditional", "moves": [
            {"condition": {"hp_pct_below": 1.0}, "action": "attack", "weight": 50},
            {"condition": {"turn_mod": {"every": 4}}, "action": "ability", "id": "special", "weight": 100},
        ]}}
        enemy = make_combatant("Boss", is_enemy=True, ai_data=ai_data)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        # Turn 3 — special not eligible
        state.turn_count = 3
        action = pick_enemy_action(enemy, state)
        assert action["action"] == "attack"

        # Turn 4 — special eligible and heavily weighted
        state.turn_count = 4
        with patch("engine.core.scenes.battle_logic.random.choices",
                   return_value=[ai_data["ai"]["moves"][1]]):
            action = pick_enemy_action(enemy, state)
        assert action["id"] == "special"

    def test_conditional_no_eligible_falls_back_to_attack(self):
        ai_data = {"ai": {"pattern": "conditional", "moves": [
            {"condition": {"hp_pct_below": 0.1}, "action": "ability", "id": "desperation", "weight": 100},
        ]}}
        enemy = make_combatant("Boss", hp=100, hp_max=100, is_enemy=True, ai_data=ai_data)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        action = pick_enemy_action(enemy, state)

        assert action["action"] == "attack"


# ── resolve_targeting ────────────────────────────────────────

class TestResolveTargeting:
    def test_random_alive_default(self):
        enemy = make_combatant("Goblin", is_enemy=True)
        hero = make_combatant("Hero")
        state = make_battle_state([hero], [enemy])

        targets = resolve_targeting(enemy, state, "")

        assert targets == [hero]

    def test_lowest_hp(self):
        ai_data = {"targeting": {"default": "lowest_hp"}}
        enemy = make_combatant("Goblin", is_enemy=True, ai_data=ai_data)
        hero1 = make_combatant("Hero", hp=80, hp_max=100)
        hero2 = make_combatant("Ally", hp=30, hp_max=100)
        state = make_battle_state([hero1, hero2], [enemy])

        targets = resolve_targeting(enemy, state, "")

        assert targets == [hero2]

    def test_highest_hp(self):
        ai_data = {"targeting": {"default": "highest_hp"}}
        enemy = make_combatant("Goblin", is_enemy=True, ai_data=ai_data)
        hero1 = make_combatant("Hero", hp=80, hp_max=100)
        hero2 = make_combatant("Ally", hp=30, hp_max=100)
        state = make_battle_state([hero1, hero2], [enemy])

        targets = resolve_targeting(enemy, state, "")

        assert targets == [hero1]

    def test_all_party(self):
        ai_data = {"targeting": {"default": "random_alive", "overrides": [
            {"ability": "breath", "target": "all_party"},
        ]}}
        enemy = make_combatant("Dragon", is_enemy=True, ai_data=ai_data)
        hero1 = make_combatant("Hero", hp=100)
        hero2 = make_combatant("Ally", hp=100)
        state = make_battle_state([hero1, hero2], [enemy])

        targets = resolve_targeting(enemy, state, "breath")

        assert len(targets) == 2
        assert hero1 in targets
        assert hero2 in targets

    def test_self_targeting(self):
        ai_data = {"targeting": {"default": "random_alive", "overrides": [
            {"ability": "iron_shell", "target": "self"},
        ]}}
        enemy = make_combatant("Crab", is_enemy=True, ai_data=ai_data)
        state = make_battle_state([make_combatant("Hero")], [enemy])

        targets = resolve_targeting(enemy, state, "iron_shell")

        assert targets == [enemy]

    def test_override_only_for_matching_ability(self):
        ai_data = {"targeting": {"default": "random_alive", "overrides": [
            {"ability": "iron_shell", "target": "self"},
        ]}}
        enemy = make_combatant("Crab", is_enemy=True, ai_data=ai_data)
        hero = make_combatant("Hero")
        state = make_battle_state([hero], [enemy])

        # Non-matching ability uses default
        targets = resolve_targeting(enemy, state, "claw_crush")

        assert targets == [hero]


# ── resolve_enemy_turn with AI ───────────────────────────────

class TestResolveEnemyTurnWithAI:
    def test_ability_shows_ability_name(self):
        ai_data = {"ai": {"pattern": "random", "moves": [
            {"action": "ability", "id": "fire_bolt", "weight": 100},
        ]}, "targeting": {"default": "random_alive"}}
        enemy = make_combatant("Mage", atk=15, is_enemy=True, ai_data=ai_data)
        hero = make_combatant("Hero", hp=100, hp_max=100, def_=5)
        state = make_battle_state([hero], [enemy])
        state.build_turn_order()
        state.active_index = state.turn_order.index(enemy)

        msg = resolve_enemy_turn(state)

        assert "Fire Bolt" in msg
        assert hero.hp < 100

    def test_ability_all_party_hits_everyone(self):
        ai_data = {"ai": {"pattern": "random", "moves": [
            {"action": "ability", "id": "breath", "weight": 100},
        ]}, "targeting": {"default": "random_alive", "overrides": [
            {"ability": "breath", "target": "all_party"},
        ]}}
        enemy = make_combatant("Dragon", atk=20, is_enemy=True, ai_data=ai_data)
        hero1 = make_combatant("Hero", hp=100, hp_max=100, def_=5)
        hero2 = make_combatant("Ally", hp=100, hp_max=100, def_=5)
        state = make_battle_state([hero1, hero2], [enemy])
        state.build_turn_order()
        state.active_index = state.turn_order.index(enemy)

        msg = resolve_enemy_turn(state)

        assert hero1.hp < 100
        assert hero2.hp < 100
        assert "Breath" in msg

    def test_no_ai_still_does_basic_attack(self):
        enemy = make_combatant("Goblin", atk=15, is_enemy=True)
        hero = make_combatant("Hero", hp=100, hp_max=100, def_=5)
        state = make_battle_state([hero], [enemy])
        state.build_turn_order()
        state.active_index = state.turn_order.index(enemy)

        msg = resolve_enemy_turn(state)

        assert hero.hp == 90
        assert "attacked" in msg


# ── _check_condition ─────────────────────────────────────────

class TestCheckCondition:
    def test_no_condition_always_true(self):
        enemy = make_combatant("E", is_enemy=True)
        state = make_battle_state()
        assert _check_condition({}, enemy, state) is True

    def test_hp_pct_below_pass(self):
        enemy = make_combatant("E", hp=30, hp_max=100, is_enemy=True)
        state = make_battle_state()
        assert _check_condition({"condition": {"hp_pct_below": 0.5}}, enemy, state) is True

    def test_hp_pct_below_fail(self):
        enemy = make_combatant("E", hp=80, hp_max=100, is_enemy=True)
        state = make_battle_state()
        assert _check_condition({"condition": {"hp_pct_below": 0.5}}, enemy, state) is False

    def test_turn_mod_pass(self):
        enemy = make_combatant("E", is_enemy=True)
        state = make_battle_state()
        state.turn_count = 8
        assert _check_condition({"condition": {"turn_mod": {"every": 4}}}, enemy, state) is True

    def test_turn_mod_fail(self):
        enemy = make_combatant("E", is_enemy=True)
        state = make_battle_state()
        state.turn_count = 7
        assert _check_condition({"condition": {"turn_mod": {"every": 4}}}, enemy, state) is False

    def test_combined_conditions(self):
        enemy = make_combatant("E", hp=30, hp_max=100, is_enemy=True)
        state = make_battle_state()
        state.turn_count = 4
        # Both must pass
        move = {"condition": {"hp_pct_below": 0.5, "turn_mod": {"every": 4}}}
        assert _check_condition(move, enemy, state) is True

    def test_combined_conditions_one_fails(self):
        enemy = make_combatant("E", hp=80, hp_max=100, is_enemy=True)
        state = make_battle_state()
        state.turn_count = 4
        move = {"condition": {"hp_pct_below": 0.5, "turn_mod": {"every": 4}}}
        assert _check_condition(move, enemy, state) is False
