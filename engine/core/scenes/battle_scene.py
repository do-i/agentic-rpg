# engine/core/scenes/battle_scene.py
#
# Phase 4 — Battle system
# Thin orchestrator: delegates logic to battle_logic, rendering to battle_renderer.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.battle.combatant import Combatant
from engine.core.battle.battle_state import BattleState, BattlePhase
from engine.core.battle.battle_rewards import RewardCalculator
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.scenes.post_battle_scene import PostBattleScene
from engine.core.scenes.battle_logic import (
    resolve_action, resolve_enemy_turn, handle_victory, handle_defeat,
    check_result, advance_to_next_turn,
)
from engine.core.scenes.battle_renderer import BattleRenderer


class BattleScene(Scene):
    """
    Phase 4 — battle screen.
    On victory: calculates rewards, syncs party state, launches PostBattleScene.
    On defeat: returns to world map (Game Over stub — Phase 4).
    """

    def __init__(
        self,
        battle_state: BattleState,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        holder: GameStateHolder,
        scenario_path: str = "",
        boss_flag: str = "",
    ) -> None:
        self._state = battle_state
        self._scene_manager = scene_manager
        self._registry = registry
        self._holder = holder
        self._boss_flag = boss_flag
        self._reward_calc = RewardCalculator()
        self._renderer = BattleRenderer(Path(scenario_path))

        self._cmd_items: list[str] = ["Attack", "Spell", "Item", "Run"]
        self._cmd_sel: int = 0
        self._sub_items: list[dict] = []
        self._sub_sel: int = 0
        self._target_pool: list[Combatant] = []
        self._target_sel: int = 0
        self._resolve_timer: float = 0.0
        self._resolve_msg: str = ""

        self._state.build_turn_order()
        active = self._state.active
        print(f"[BATTLE START] First active: {active.name if active else 'None'} | is_enemy={active.is_enemy if active else False}")
        if active and active.is_enemy:
            self._state.phase = BattlePhase.ENEMY_TURN
            self._do_enemy_turn()
        else:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._cmd_sel = 0

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if not events:
            return

        for event in events:
            if event.type == pygame.QUIT:
                continue

            if event.type != pygame.KEYDOWN:
                continue

            phase = self._state.phase

            if event.key == pygame.K_ESCAPE:
                if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM, BattlePhase.SELECT_TARGET):
                    self._state.phase = BattlePhase.PLAYER_TURN
                    self._sub_items.clear()
                    continue
                elif phase == BattlePhase.PLAYER_TURN:
                    self._attempt_run()
                    continue

            if phase == BattlePhase.PLAYER_TURN:
                self._handle_cmd(event.key)
            elif phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
                self._handle_sub(event.key)
            elif phase == BattlePhase.SELECT_TARGET:
                self._handle_target(event.key)
            elif phase == BattlePhase.RESOLVE:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self._resolve_timer = 0.0
            elif phase in (BattlePhase.POST_BATTLE, BattlePhase.GAME_OVER):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    if phase == BattlePhase.GAME_OVER:
                        self._return_to_world_map()

    def _handle_cmd(self, key: int) -> None:
        active = self._state.active
        if active is None or active.is_enemy:
            return
        if key == pygame.K_UP:
            self._cmd_sel = max(0, self._cmd_sel - 1)
        elif key == pygame.K_DOWN:
            self._cmd_sel = min(len(self._cmd_items) - 1, self._cmd_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RIGHT):
            self._confirm_cmd()

    def _confirm_cmd(self) -> None:
        label  = self._cmd_items[self._cmd_sel]
        active = self._state.active
        if label == "Attack":
            self._target_pool = self._state.alive_enemies()
            self._target_sel  = 0
            self._state.pending_action = {"type": "attack", "source": active}
            self._state.phase = BattlePhase.SELECT_TARGET
        elif label == "Spell":
            if active and active.mp_max > 0:
                self._open_spell_menu(active)
        elif label == "Item":
            self._open_item_menu()
        elif label == "Run":
            self._attempt_run()

    def _open_spell_menu(self, active: Combatant) -> None:
        self._sub_items = []
        for ab in active.abilities:
            if ab.get("type") not in ("spell", "heal", "buff", "debuff", "utility"):
                continue
            cost = ab.get("mp_cost", 0)
            self._sub_items.append({
                "label":    ab["name"],
                "mp_cost":  cost,
                "data":     ab,
                "disabled": active.mp < cost,
            })
        self._sub_sel = 0
        self._state.phase = BattlePhase.SELECT_SPELL

    def _open_item_menu(self) -> None:
        self._sub_items = [
            {"label": "Potion",    "qty": 5, "data": {"id": "potion"},    "disabled": False},
            {"label": "Hi-Potion", "qty": 3, "data": {"id": "hi_potion"}, "disabled": False},
            {"label": "Antidote",  "qty": 2, "data": {"id": "antidote"},  "disabled": False},
        ]
        self._sub_sel = 0
        self._state.phase = BattlePhase.SELECT_ITEM

    def _handle_sub(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_LEFT):
            self._state.phase = BattlePhase.PLAYER_TURN
            return
        if key == pygame.K_UP:
            self._sub_sel = max(0, self._sub_sel - 1)
        elif key == pygame.K_DOWN:
            self._sub_sel = min(len(self._sub_items) - 1, self._sub_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_RIGHT):
            self._confirm_sub()

    def _confirm_sub(self) -> None:
        if not self._sub_items:
            return
        item    = self._sub_items[self._sub_sel]
        if item.get("disabled"):
            return
        active  = self._state.active
        phase   = self._state.phase
        ab_data = item.get("data", {})
        target  = ab_data.get("target", "single_enemy")

        action_type = "spell" if phase == BattlePhase.SELECT_SPELL else "item"

        if target == "single_enemy":
            self._target_pool = self._state.alive_enemies()
            self._target_sel  = 0
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        elif target == "single_ally":
            self._target_pool = self._state.alive_party()
            self._target_sel  = 0
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        elif target == "single_ko":
            pool = self._state.ko_party()
            if not pool:
                return
            self._target_pool = pool
            self._target_sel  = 0
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        elif target in ("all_allies", "party"):
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": self._state.alive_party(),
            }
            self._do_resolve()
        elif target in ("all_enemies", "group_enemies"):
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": self._state.alive_enemies(),
            }
            self._do_resolve()
        elif target == "self":
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": [active],
            }
            self._do_resolve()
        else:
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": self._state.alive_enemies(),
            }
            self._do_resolve()

    def _handle_target(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._sub_items.clear()
            return

        if key in (pygame.K_LEFT, pygame.K_UP):
            self._target_sel = max(0, self._target_sel - 1)
        elif key in (pygame.K_RIGHT, pygame.K_DOWN):
            self._target_sel = min(len(self._target_pool) - 1, self._target_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._target_pool:
                self._state.pending_action["targets"] = [self._target_pool[self._target_sel]]
                self._do_resolve()

    # ── Action resolution (delegates to battle_logic) ─────────

    def _do_resolve(self) -> None:
        msg = resolve_action(self._state)
        self._enter_resolve(msg)

    def _enter_resolve(self, msg: str) -> None:
        self._resolve_msg = msg
        self._resolve_timer = 3.0
        self._state.phase = BattlePhase.RESOLVE

    def _do_enemy_turn(self) -> None:
        msg = resolve_enemy_turn(self._state)
        if msg:
            self._enter_resolve(msg)
        else:
            self._check_result()

    def _check_result(self) -> None:
        print(f"[DEBUG] _check_result called | phase={self._state.phase} | active={self._state.active.name if self._state.active else None}")
        result = check_result(self._state)
        if result == "victory":
            rewards = handle_victory(
                self._state, self._holder, self._boss_flag, self._reward_calc,
            )
            self._scene_manager.switch(PostBattleScene(
                rewards=rewards,
                scene_manager=self._scene_manager,
                registry=self._registry,
                on_continue=self._return_to_world_map,
            ))
            return
        if result == "defeat":
            handle_defeat(self._state)
            self._scene_manager.switch(self._registry.get("world_map"))
            return

        advance_to_next_turn(self._state)
        if self._state.phase == BattlePhase.ENEMY_TURN:
            self._do_enemy_turn()
        else:
            self._cmd_sel = 0

    def _attempt_run(self) -> None:
        self._scene_manager.switch(self._registry.get("world_map"))

    def _return_to_world_map(self) -> None:
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        self._state.update_floats(delta)
        if self._state.phase == BattlePhase.RESOLVE:
            self._resolve_timer -= delta
            if self._resolve_timer <= 0:
                self._resolve_msg = ""
                self._check_result()
        elif self._state.phase == BattlePhase.ENEMY_TURN:
            self._do_enemy_turn()

    # ── Render (delegates to BattleRenderer) ──────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen, self._state,
            self._cmd_items, self._cmd_sel,
            self._sub_items, self._sub_sel,
            self._target_pool, self._target_sel,
            self._resolve_msg,
        )
