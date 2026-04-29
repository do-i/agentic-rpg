# engine/battle/battle_scene.py
#
# Phase 4 — Battle system
# Thin orchestrator: delegates input to BattleInputController, sub-menu
# building to battle_menu_builder, logic to battle_logic, rendering to
# BattleRenderer.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.battle.combatant import Combatant
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.battle_rewards import RewardCalculator
from engine.battle.battle_input import BattleInputController, BattleInputCallbacks
from engine.battle.battle_menu_builder import build_spell_menu, build_item_menu
from engine.common.game_state_holder import GameStateHolder
from engine.battle.post_battle_scene import PostBattleScene
from engine.battle.game_over_scene import GameOverScene
from engine.battle.battle_logic import (
    resolve_action, handle_victory, handle_defeat,
    check_result, advance_to_next_turn, attempt_flee,
    tick_active_end_of_turn, skip_if_incapacitated,
)
from engine.battle.battle_enemy_logic import resolve_enemy_turn
from engine.battle.battle_renderer import BattleRenderer
from engine.battle.battle_fx import BattleFx
from engine.item.item_effect_handler import ItemEffectHandler
from engine.io.save_manager import GameStateManager
from engine.audio.bgm_manager import BgmManager
from engine.audio.sfx_manager import SfxManager
from engine.util.pseudo_random import PseudoRandom


class BattleScene(Scene):
    """
    Battle screen.
    On victory: calculates rewards, syncs party state, launches PostBattleScene.
    On defeat: launches GameOverScene with load/title/quit options.
    """

    def __init__(
        self,
        battle_state: BattleState,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        holder: GameStateHolder,
        screen_width: int,
        screen_height: int,
        *,
        scenario_path: str = "",
        boss_flag: str = "",
        effect_handler: ItemEffectHandler | None = None,
        game_state_manager: GameStateManager | None = None,
        bgm_manager: BgmManager | None = None,
        sfx_manager: SfxManager | None = None,
        rng: PseudoRandom | None = None,
        balance=None,
    ) -> None:
        self._state = battle_state
        self._scene_manager = scene_manager
        self._registry = registry
        self._holder = holder
        self._boss_flag = boss_flag
        self._effect_handler = effect_handler
        self._game_state_manager = game_state_manager
        self._rng = rng
        self._balance = balance
        self._reward_calc = RewardCalculator(rng, balance)
        self._screen_width = screen_width
        self._renderer = BattleRenderer(Path(scenario_path), screen_width, screen_height)
        self._bgm_manager = bgm_manager
        self._bgm_started = False
        self._sfx_manager = sfx_manager
        self._encounter_sfx_played = False
        self._fx = BattleFx()

        # Resolve battle BGM key (played lazily on first render)
        self._bgm_key: str | None = None
        if scenario_path:
            boss = any(e.boss for e in battle_state.enemies)
            self._bgm_key = "battle.boss" if boss else "battle.normal"

        self._input = BattleInputController(
            BattleInputCallbacks(
                do_resolve=self._do_resolve,
                open_spell_menu=self._open_spell_menu,
                open_item_menu=self._open_item_menu,
                attempt_run=self._attempt_run,
                enter_resolve=self._enter_resolve,
            ),
            sfx_manager=sfx_manager,
        )
        self._resolve_msg: str = ""
        self._resolve_is_enemy: bool = False

        self._state.build_turn_order()
        active = self._state.active
        if self._state.barrier_messages:
            self._enter_resolve(self._state.barrier_messages[0])
        elif active and active.is_enemy:
            self._state.phase = BattlePhase.ENEMY_TURN
            self._do_enemy_turn()
        else:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._input.reset_cmd_selection()

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
                    self._input.clear_sub()
                    # Drop the pending action so a stale partially-built dict
                    # can't leak into the next confirm. The next confirm
                    # would overwrite it anyway, but holding it is fragile.
                    self._state.pending_action = None
                    continue
                elif phase == BattlePhase.PLAYER_TURN:
                    self._attempt_run()
                    continue

            if phase == BattlePhase.PLAYER_TURN:
                self._input.handle_cmd(self._state, event.key)
            elif phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
                self._input.handle_sub(self._state, event.key)
            elif phase == BattlePhase.SELECT_TARGET:
                self._input.handle_target(self._state, event.key)
            elif phase == BattlePhase.RESOLVE:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._resolve_msg = ""
                    self._check_result()
            elif phase in (BattlePhase.POST_BATTLE, BattlePhase.GAME_OVER):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    if phase == BattlePhase.GAME_OVER:
                        self._return_to_world_map()

    def _open_spell_menu(self, active: Combatant) -> None:
        self._input.set_sub_items(build_spell_menu(active))
        self._state.phase = BattlePhase.SELECT_SPELL

    def _open_item_menu(self) -> None:
        repo = self._holder.get().repository
        self._input.set_sub_items(build_item_menu(repo, self._effect_handler))
        self._state.phase = BattlePhase.SELECT_ITEM

    # ── Action resolution (delegates to battle_logic) ─────────

    def _do_resolve(self) -> None:
        repo = self._holder.get().repository
        pending = dict(self._state.pending_action) if self._state.pending_action else {}
        alive_before = {e.name for e in self._state.enemies if not e.is_ko}
        msg = resolve_action(self._state, self._screen_width,
                             effect_handler=self._effect_handler, repository=repo,
                             rng=self._rng, fx=self._fx)
        if self._sfx_manager:
            self._sfx_manager.play_battle_action(pending)
            newly_ko = [e for e in self._state.enemies if e.is_ko and e.name in alive_before]
            if newly_ko:
                self._sfx_manager.play("enemy_death")
        self._enter_resolve(msg)

    def _enter_resolve(self, msg: str, is_enemy: bool = False) -> None:
        self._resolve_msg = msg
        self._resolve_is_enemy = is_enemy
        self._state.phase = BattlePhase.RESOLVE

    def _do_enemy_turn(self) -> None:
        msg = resolve_enemy_turn(self._state, self._screen_width,
                                 sfx_manager=self._sfx_manager,
                                 rng=self._rng, fx=self._fx)
        if msg:
            self._enter_resolve(msg, is_enemy=True)
        else:
            self._check_result()

    def _check_result(self) -> None:
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
                sfx_manager=self._sfx_manager,
            ))
            return
        if result == "defeat":
            handle_defeat(self._state)
            self._scene_manager.switch(GameOverScene(
                scene_manager=self._scene_manager,
                registry=self._registry,
                holder=self._holder,
                game_state_manager=self._game_state_manager,
                sfx_manager=self._sfx_manager,
            ))
            return

        tick_msg = tick_active_end_of_turn(self._state, self._screen_width)
        # Burn DOT may have just KO'd the active combatant or wiped a side.
        post_tick = check_result(self._state)
        if post_tick != "continue":
            if tick_msg:
                self._enter_resolve(tick_msg, is_enemy=self._state.active.is_enemy if self._state.active else False)
                return
            self._check_result()
            return

        advance_to_next_turn(self._state)
        skip_msg = skip_if_incapacitated(self._state)
        msg = tick_msg
        if skip_msg:
            msg = f"{msg}  {skip_msg}" if msg else skip_msg
        if msg:
            self._enter_resolve(msg)
            return

        if self._state.phase == BattlePhase.ENEMY_TURN:
            self._do_enemy_turn()
        else:
            self._input.reset_cmd_selection()

    def _attempt_run(self) -> None:
        success, msg = attempt_flee(self._state, self._holder, self._rng, self._balance)
        if self._sfx_manager:
            self._sfx_manager.play("flee" if success else "denied")
        if success:
            self._scene_manager.switch(self._registry.get("world_map"))
        else:
            self._enter_resolve(msg)

    def _return_to_world_map(self) -> None:
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        self._state.update_floats(delta)
        self._fx.update(delta)
        if self._state.phase == BattlePhase.ENEMY_TURN:
            self._do_enemy_turn()

    # ── Render (delegates to BattleRenderer) ──────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._bgm_started and self._bgm_manager and self._bgm_key:
            self._bgm_started = True
            self._bgm_manager.play_key(self._bgm_key)
        if not self._encounter_sfx_played and self._sfx_manager:
            self._encounter_sfx_played = True
            self._sfx_manager.play("encounter")
        self._renderer.render(
            screen, self._state,
            self._input.cmd_items, self._input.cmd_sel,
            self._input.sub_items, self._input.sub_sel,
            self._input.target_pool, self._input.target_sel,
            self._resolve_msg,
            self._resolve_is_enemy,
            fx=self._fx,
        )
