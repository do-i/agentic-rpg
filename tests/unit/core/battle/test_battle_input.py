# tests/unit/core/battle/test_battle_input.py

import pygame
import pytest
from unittest.mock import MagicMock

from engine.battle.battle_input import (
    BattleInputController, BattleInputCallbacks, CMD_LABELS,
)
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant


def make_combatant(name="Hero", is_enemy=False, mp=20, mp_max=20,
                   silenced=False, abilities=None) -> Combatant:
    c = Combatant(
        id=name.lower(), name=name,
        hp=100, hp_max=100, mp=mp, mp_max=mp_max,
        atk=10, def_=5, mres=5, dex=10,
        is_enemy=is_enemy, boss=False,
        abilities=abilities or [], ai_data={},
    )
    if silenced:
        from engine.battle.combatant import StatusEffect, ActiveStatus
        c.status_effects.append(ActiveStatus(effect=StatusEffect.SILENCE, duration_turns=2))
    return c


def make_state(party=None, enemies=None, phase=BattlePhase.PLAYER_TURN) -> BattleState:
    p = party or [make_combatant("Hero")]
    e = enemies or [make_combatant("Slime", is_enemy=True)]
    state = BattleState(party=p, enemies=e, phase=phase)
    state.build_turn_order()
    return state


def make_controller(sfx=None, **callback_overrides):
    callbacks = BattleInputCallbacks(
        do_resolve=MagicMock(),
        open_spell_menu=MagicMock(),
        open_item_menu=MagicMock(),
        attempt_run=MagicMock(),
        enter_resolve=MagicMock(),
    )
    for k, v in callback_overrides.items():
        setattr(callbacks, k, v)
    return BattleInputController(callbacks, sfx_manager=sfx), callbacks


# ── handle_cmd ────────────────────────────────────────────────

class TestHandleCmd:
    def test_initial_selection_is_attack(self):
        ctl, _ = make_controller()
        assert ctl.cmd_items[ctl.cmd_sel] == "Attack"

    def test_down_advances_selection(self):
        ctl, _ = make_controller()
        state = make_state()
        ctl.handle_cmd(state, pygame.K_DOWN)
        assert ctl.cmd_sel == 1

    def test_up_clamps_at_zero(self):
        ctl, _ = make_controller()
        state = make_state()
        ctl.handle_cmd(state, pygame.K_UP)
        assert ctl.cmd_sel == 0

    def test_down_clamps_at_end(self):
        ctl, _ = make_controller()
        state = make_state()
        for _ in range(10):
            ctl.handle_cmd(state, pygame.K_DOWN)
        assert ctl.cmd_sel == len(CMD_LABELS) - 1

    def test_hover_sfx_plays_when_selection_changes(self):
        sfx = MagicMock()
        ctl, _ = make_controller(sfx=sfx)
        state = make_state()
        ctl.handle_cmd(state, pygame.K_DOWN)
        assert ("hover",) in [c.args for c in sfx.play.call_args_list]

    def test_hover_sfx_silent_at_clamp(self):
        sfx = MagicMock()
        ctl, _ = make_controller(sfx=sfx)
        state = make_state()
        ctl.handle_cmd(state, pygame.K_UP)  # already at 0
        sfx.play.assert_not_called()

    def test_ignored_when_active_is_enemy(self):
        ctl, _ = make_controller()
        state = make_state(party=[make_combatant("H")],
                           enemies=[make_combatant("E", is_enemy=True)])
        # Force active to enemy
        state.turn_order = [state.enemies[0]]
        state.active_index = 0
        ctl.handle_cmd(state, pygame.K_DOWN)
        assert ctl.cmd_sel == 0

    def test_attack_confirm_sets_pending_and_target_pool(self):
        ctl, cb = make_controller()
        e1 = make_combatant("E1", is_enemy=True)
        e2 = make_combatant("E2", is_enemy=True)
        state = make_state(enemies=[e1, e2])
        ctl.cmd_sel = 0  # Attack
        ctl.handle_cmd(state, pygame.K_RETURN)
        assert state.phase == BattlePhase.SELECT_TARGET
        assert state.pending_action["type"] == "attack"
        assert ctl.target_pool == [e1, e2]
        cb.do_resolve.assert_not_called()

    def test_defend_triggers_resolve_immediately(self):
        ctl, cb = make_controller()
        state = make_state()
        ctl.cmd_sel = 1  # Defend
        ctl.handle_cmd(state, pygame.K_RETURN)
        assert state.pending_action["type"] == "defend"
        cb.do_resolve.assert_called_once()

    def test_spell_when_silenced_enters_resolve_with_message(self):
        ctl, cb = make_controller()
        hero = make_combatant("Hero", silenced=True)
        state = make_state(party=[hero])
        ctl.cmd_sel = 2  # Spell
        ctl.handle_cmd(state, pygame.K_RETURN)
        cb.enter_resolve.assert_called_once()
        msg = cb.enter_resolve.call_args.args[0]
        assert "silenced" in msg

    def test_spell_when_no_mp_max_does_not_open_menu(self):
        ctl, cb = make_controller()
        hero = make_combatant("Hero", mp=0, mp_max=0)
        state = make_state(party=[hero])
        ctl.cmd_sel = 2
        ctl.handle_cmd(state, pygame.K_RETURN)
        cb.open_spell_menu.assert_not_called()

    def test_spell_with_mp_pool_opens_menu(self):
        ctl, cb = make_controller()
        state = make_state()
        ctl.cmd_sel = 2
        ctl.handle_cmd(state, pygame.K_RETURN)
        cb.open_spell_menu.assert_called_once()

    def test_item_opens_menu(self):
        ctl, cb = make_controller()
        state = make_state()
        ctl.cmd_sel = 3
        ctl.handle_cmd(state, pygame.K_RETURN)
        cb.open_item_menu.assert_called_once()

    def test_run_invokes_attempt_run(self):
        ctl, cb = make_controller()
        state = make_state()
        ctl.cmd_sel = 4
        ctl.handle_cmd(state, pygame.K_RETURN)
        cb.attempt_run.assert_called_once()


# ── handle_sub ────────────────────────────────────────────────

class TestHandleSub:
    def test_escape_returns_to_player_turn(self):
        sfx = MagicMock()
        ctl, _ = make_controller(sfx=sfx)
        state = make_state(phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_ESCAPE)
        assert state.phase == BattlePhase.PLAYER_TURN

    def test_left_returns_to_player_turn(self):
        ctl, _ = make_controller()
        state = make_state(phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_LEFT)
        assert state.phase == BattlePhase.PLAYER_TURN

    def test_down_navigates_within_pool(self):
        ctl, _ = make_controller()
        ctl.set_sub_items([{"label": "A", "data": {}}, {"label": "B", "data": {}}])
        state = make_state(phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_DOWN)
        assert ctl.sub_sel == 1

    def test_disabled_row_does_not_resolve(self):
        ctl, cb = make_controller()
        ctl.set_sub_items([{"label": "Pricey", "data": {}, "disabled": True}])
        state = make_state(phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_RETURN)
        cb.do_resolve.assert_not_called()
        # Still on SELECT_SPELL because the click was a no-op
        assert state.phase == BattlePhase.SELECT_SPELL

    def test_single_enemy_target_enters_select_target(self):
        ctl, cb = make_controller()
        ctl.set_sub_items([{"label": "Fire", "data": {"name": "Fire", "target": "single_enemy"}}])
        e = make_combatant("E", is_enemy=True)
        state = make_state(enemies=[e], phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_RETURN)
        assert state.phase == BattlePhase.SELECT_TARGET
        assert ctl.target_pool == [e]
        assert state.pending_action["type"] == "spell"
        cb.do_resolve.assert_not_called()

    def test_self_target_resolves_immediately(self):
        ctl, cb = make_controller()
        ctl.set_sub_items([{"label": "Focus", "data": {"target": "self"}}])
        state = make_state(phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_RETURN)
        cb.do_resolve.assert_called_once()
        assert state.pending_action["targets"] == [state.active]

    def test_all_allies_target_resolves(self):
        ctl, cb = make_controller()
        ctl.set_sub_items([{"label": "Aoe", "data": {"target": "all_allies"}}])
        state = make_state(phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_RETURN)
        cb.do_resolve.assert_called_once()
        assert state.pending_action["targets"] == state.alive_party()

    def test_all_enemies_target_resolves(self):
        ctl, cb = make_controller()
        ctl.set_sub_items([{"label": "Aoe", "data": {"target": "all_enemies"}}])
        e1 = make_combatant("E1", is_enemy=True)
        e2 = make_combatant("E2", is_enemy=True)
        state = make_state(enemies=[e1, e2], phase=BattlePhase.SELECT_SPELL)
        ctl.handle_sub(state, pygame.K_RETURN)
        cb.do_resolve.assert_called_once()
        assert set(id(t) for t in state.pending_action["targets"]) == {id(e1), id(e2)}

    def test_single_ko_with_no_ko_targets_no_op(self):
        ctl, cb = make_controller()
        ctl.set_sub_items([{"label": "Phoenix", "data": {"target": "single_ko"}}])
        state = make_state(phase=BattlePhase.SELECT_ITEM)
        ctl.handle_sub(state, pygame.K_RETURN)
        # No KO'd party members → silent no-op, stay on SELECT_ITEM
        assert state.phase == BattlePhase.SELECT_ITEM
        cb.do_resolve.assert_not_called()

    def test_action_type_uses_phase(self):
        ctl, _ = make_controller()
        ctl.set_sub_items([{"label": "x", "data": {"target": "self"}}])
        state = make_state(phase=BattlePhase.SELECT_ITEM)
        ctl.handle_sub(state, pygame.K_RETURN)
        assert state.pending_action["type"] == "item"


# ── handle_target ─────────────────────────────────────────────

class TestHandleTarget:
    def test_escape_clears_sub_items_and_returns_to_player_turn(self):
        ctl, _ = make_controller()
        ctl.set_sub_items([{"label": "x"}])
        state = make_state(phase=BattlePhase.SELECT_TARGET)
        ctl.handle_target(state, pygame.K_ESCAPE)
        assert state.phase == BattlePhase.PLAYER_TURN
        assert ctl.sub_items == []

    def test_left_decrements_target_sel(self):
        ctl, _ = make_controller()
        e1 = make_combatant("E1", is_enemy=True)
        e2 = make_combatant("E2", is_enemy=True)
        ctl.set_target_pool([e1, e2])
        ctl.target_sel = 1
        state = make_state(phase=BattlePhase.SELECT_TARGET)
        ctl.handle_target(state, pygame.K_LEFT)
        assert ctl.target_sel == 0

    def test_right_increments_within_bounds(self):
        ctl, _ = make_controller()
        e1 = make_combatant("E1", is_enemy=True)
        e2 = make_combatant("E2", is_enemy=True)
        ctl.set_target_pool([e1, e2])
        state = make_state(phase=BattlePhase.SELECT_TARGET)
        ctl.handle_target(state, pygame.K_RIGHT)
        assert ctl.target_sel == 1

    def test_confirm_with_empty_pool_is_silent_no_op(self):
        ctl, cb = make_controller()
        state = make_state(phase=BattlePhase.SELECT_TARGET)
        ctl.handle_target(state, pygame.K_RETURN)
        cb.do_resolve.assert_not_called()

    def test_confirm_writes_target_and_resolves(self):
        ctl, cb = make_controller()
        e = make_combatant("E", is_enemy=True)
        ctl.set_target_pool([e])
        state = make_state(phase=BattlePhase.SELECT_TARGET)
        state.pending_action = {"type": "attack", "source": state.active}
        ctl.handle_target(state, pygame.K_RETURN)
        assert state.pending_action["targets"] == [e]
        cb.do_resolve.assert_called_once()


# ── lifecycle helpers ────────────────────────────────────────

class TestLifecycleHelpers:
    def test_set_sub_items_resets_sel(self):
        ctl, _ = make_controller()
        ctl.sub_sel = 4
        ctl.set_sub_items([{"a": 1}, {"b": 2}])
        assert ctl.sub_sel == 0

    def test_set_target_pool_resets_sel(self):
        ctl, _ = make_controller()
        ctl.target_sel = 3
        ctl.set_target_pool([make_combatant("E", is_enemy=True)])
        assert ctl.target_sel == 0

    def test_clear_sub_empties(self):
        ctl, _ = make_controller()
        ctl.sub_items = [{"x": 1}]
        ctl.clear_sub()
        assert ctl.sub_items == []

    def test_reset_cmd_selection(self):
        ctl, _ = make_controller()
        ctl.cmd_sel = 3
        ctl.reset_cmd_selection()
        assert ctl.cmd_sel == 0
