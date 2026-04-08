# engine/scenes/status_scene.py
#
# Thin orchestrator: delegates logic to status_logic, rendering to status_renderer.

from __future__ import annotations

import pygame
from engine.scenes.scene import Scene
from engine.scenes.scene_manager import SceneManager
from engine.scenes.scene_registry import SceneRegistry
from engine.dto.game_state_holder import GameStateHolder
from engine.dto.member_state import MemberState
from engine.ui.target_select_overlay import TargetSelectOverlay
from engine.service.status_logic import (
    field_spells, valid_targets, apply_spell, apply_spell_all,
)
from engine.ui.status_renderer import StatusRenderer

TOAST_DUR = 1.2


class StatusScene(Scene):
    """
    Full-screen party status overview.
    Reads directly from GameState.party — no hardcoded data.
    S / ESC to close.  ENTER to open spell list for selected member.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str = "",
        return_scene_name: str = "world_map",
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._return_scene_name = return_scene_name
        self._scenario_path = scenario_path
        self._selected = 0
        self._renderer = StatusRenderer(scenario_path)

        # spell sub-menu state
        self._spell_list: list[dict] | None = None
        self._spell_sel: int = 0
        self._spell_caster: MemberState | None = None
        self._target_overlay: TargetSelectOverlay | None = None
        self._toast_text: str = ""
        self._toast_timer: float = 0.0

    @property
    def _fonts_ready(self) -> bool:
        return self._renderer.fonts_ready

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return

        if self._toast_timer > 0:
            return

        members = self._holder.get().party.members
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self._spell_list is not None:
                self._handle_spell_key(event.key)
                return

            if event.key in (pygame.K_s, pygame.K_ESCAPE):
                self._scene_manager.switch(self._registry.get(self._return_scene_name))
            elif event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(members) - 1, self._selected + 1)
            elif event.key == pygame.K_RETURN:
                self._open_spell_menu()

    def _open_spell_menu(self) -> None:
        members = self._holder.get().party.members
        if not members:
            return
        member = members[self._selected]
        spells = field_spells(member, self._scenario_path)
        if not spells:
            self._toast_text = f"{member.name} has no field spells."
            self._toast_timer = TOAST_DUR
            return
        self._spell_caster = member
        self._spell_list = spells
        self._spell_sel = 0

    def _handle_spell_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._spell_list = None
            self._spell_caster = None
            return

        spells = self._spell_list
        if key == pygame.K_UP:
            self._spell_sel = max(0, self._spell_sel - 1)
        elif key == pygame.K_DOWN:
            self._spell_sel = min(len(spells) - 1, self._spell_sel + 1)
        elif key == pygame.K_RETURN:
            spell = spells[self._spell_sel]
            cost = spell.get("mp_cost", 0)
            if cost > self._spell_caster.mp:
                return
            target_type = spell.get("target", "single_ally")
            if target_type in ("all_allies", "party"):
                members = self._holder.get().party.members
                msg = apply_spell_all(spell, self._spell_caster, members)
                self._spell_list = None
                self._toast_text = msg
                self._toast_timer = TOAST_DUR
            else:
                members = self._holder.get().party.members
                targets = valid_targets(spell, members)
                if not targets:
                    self._toast_text = "No valid targets."
                    self._toast_timer = TOAST_DUR
                    self._spell_list = None
                    return
                pending_spell = spell
                caster = self._spell_caster
                self._target_overlay = TargetSelectOverlay(
                    targets=targets,
                    item_label=spell["name"],
                    on_confirm=lambda t, s=pending_spell, c=caster: self._on_target_confirm(s, c, t),
                    on_cancel=self._on_target_cancel,
                )

    def _on_target_confirm(self, spell: dict, caster: MemberState, target: MemberState) -> None:
        msg = apply_spell(spell, caster, target)
        self._target_overlay = None
        self._spell_list = None
        self._spell_caster = None
        self._toast_text = msg
        self._toast_timer = TOAST_DUR

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._toast_timer > 0:
            self._toast_timer -= delta

    # ── Render (delegates to StatusRenderer) ──────────────────

    def render(self, screen: pygame.Surface) -> None:
        state   = self._holder.get()
        members = state.party.members

        self._renderer.render(
            screen, members,
            gp=state.repository.gp,
            selected=self._selected,
            spell_list=self._spell_list,
            spell_sel=self._spell_sel,
            spell_caster=self._spell_caster,
            target_overlay=self._target_overlay,
            toast_text=self._toast_text,
            toast_timer=self._toast_timer,
        )
