# engine/battle/battle_input.py
#
# Player-side input handling for BattleScene. Owns the selection-tracking
# state (command/sub/target indices and pools) and exposes one handler per
# input phase. The scene wires callbacks for the "what happens after a
# confirm" branches: open spell/item menu, attempt run, enter resolve,
# and the catch-all do_resolve when an action is fully specified.
#
# Hover/confirm/cancel SFX live here so the scene doesn't need to thread
# the SFX manager through every nav branch.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant


CMD_LABELS = ("Attack", "Defend", "Spell", "Item", "Run")


@dataclass
class BattleInputCallbacks:
    """Outbound effects the input controller can trigger.

    The scene supplies these so the controller stays oblivious to the
    rest of the orchestration (resolve, scene transitions, etc).
    """
    do_resolve:      Callable[[], None]
    open_spell_menu: Callable[[Combatant], None]
    open_item_menu:  Callable[[], None]
    attempt_run:     Callable[[], None]
    enter_resolve:   Callable[[str, bool], None]   # (msg, is_enemy)


class BattleInputController:
    """Owns the player-side selection state and routes per-phase input."""

    def __init__(self, callbacks: BattleInputCallbacks, sfx_manager=None) -> None:
        self._callbacks = callbacks
        self._sfx_manager = sfx_manager

        self.cmd_items: list[str]       = list(CMD_LABELS)
        self.cmd_sel: int               = 0
        self.sub_items: list[dict]      = []
        self.sub_sel: int               = 0
        self.target_pool: list[Combatant] = []
        self.target_sel: int            = 0

    # ── Lifecycle helpers ────────────────────────────────────

    def reset_cmd_selection(self) -> None:
        self.cmd_sel = 0

    def clear_sub(self) -> None:
        self.sub_items.clear()

    def set_sub_items(self, items: list[dict]) -> None:
        self.sub_items = items
        self.sub_sel = 0

    def set_target_pool(self, pool: list[Combatant]) -> None:
        self.target_pool = pool
        self.target_sel = 0

    # ── Per-phase input ──────────────────────────────────────

    def handle_cmd(self, state: BattleState, key: int) -> None:
        active = state.active
        if active is None or active.is_enemy:
            return
        if key == pygame.K_UP:
            self._move_sel("cmd_sel", -1, len(self.cmd_items))
        elif key == pygame.K_DOWN:
            self._move_sel("cmd_sel", +1, len(self.cmd_items))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RIGHT):
            self._play("confirm")
            self._confirm_cmd(state)

    def handle_sub(self, state: BattleState, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_LEFT):
            self._play("cancel")
            state.phase = BattlePhase.PLAYER_TURN
            return
        if key == pygame.K_UP:
            self._move_sel("sub_sel", -1, len(self.sub_items))
        elif key == pygame.K_DOWN:
            self._move_sel("sub_sel", +1, len(self.sub_items))
        elif key in (pygame.K_RETURN, pygame.K_RIGHT):
            self._play("confirm")
            self._confirm_sub(state)

    def handle_target(self, state: BattleState, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._play("cancel")
            state.phase = BattlePhase.PLAYER_TURN
            self.clear_sub()
            # Match the scene-level ESC path (§1.10): drop the pending
            # action so the next confirm starts from a clean slot.
            state.pending_action = None
            return
        if key in (pygame.K_LEFT, pygame.K_UP):
            self._move_sel("target_sel", -1, len(self.target_pool))
        elif key in (pygame.K_RIGHT, pygame.K_DOWN):
            self._move_sel("target_sel", +1, len(self.target_pool))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.target_pool:
                self._play("confirm")
                state.pending_action["targets"] = [self.target_pool[self.target_sel]]
                self._callbacks.do_resolve()

    # ── Confirm dispatch ─────────────────────────────────────

    def _confirm_cmd(self, state: BattleState) -> None:
        label  = self.cmd_items[self.cmd_sel]
        active = state.active
        if label == "Attack":
            self.set_target_pool(state.alive_enemies())
            state.pending_action = {"type": "attack", "source": active}
            state.phase = BattlePhase.SELECT_TARGET
        elif label == "Defend":
            state.pending_action = {
                "type": "defend", "source": active, "targets": [active],
            }
            self._callbacks.do_resolve()
        elif label == "Spell":
            if active and active.is_silenced:
                self._play("denied")
                self._callbacks.enter_resolve(f"{active.name} is silenced!", False)
                return
            if active and active.mp_max > 0:
                self._callbacks.open_spell_menu(active)
        elif label == "Item":
            self._callbacks.open_item_menu()
        elif label == "Run":
            self._callbacks.attempt_run()

    def _confirm_sub(self, state: BattleState) -> None:
        if not self.sub_items:
            return
        item = self.sub_items[self.sub_sel]
        if item.get("disabled"):
            return
        active  = state.active
        phase   = state.phase
        ab_data = item.get("data", {})
        target  = ab_data.get("target", "single_enemy")

        action_type = "spell" if phase == BattlePhase.SELECT_SPELL else "item"

        if target == "single_enemy":
            self.set_target_pool(state.alive_enemies())
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            state.phase = BattlePhase.SELECT_TARGET
        elif target == "single_ally":
            self.set_target_pool(state.alive_party())
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            state.phase = BattlePhase.SELECT_TARGET
        elif target == "single_ko":
            pool = state.ko_party()
            if not pool:
                return
            self.set_target_pool(pool)
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            state.phase = BattlePhase.SELECT_TARGET
        elif target in ("all_allies", "party"):
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": state.alive_party(),
            }
            self._callbacks.do_resolve()
        elif target in ("all_enemies", "group_enemies"):
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": state.alive_enemies(),
            }
            self._callbacks.do_resolve()
        elif target == "self":
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": [active],
            }
            self._callbacks.do_resolve()
        else:
            state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": state.alive_enemies(),
            }
            self._callbacks.do_resolve()

    # ── Internals ────────────────────────────────────────────

    def _move_sel(self, attr: str, delta: int, length: int) -> None:
        if length <= 0:
            return
        cur = getattr(self, attr)
        new = max(0, min(length - 1, cur + delta))
        if new != cur:
            self._play("hover")
        setattr(self, attr, new)

    def _play(self, key: str) -> None:
        if self._sfx_manager:
            self._sfx_manager.play(key)
