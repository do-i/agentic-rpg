# engine/field_menu/field_menu_scene.py
#
# Pause / field menu — opened from the world map (M key).
# Lists party-wide actions: Items, Status, Equipment, Spells, Save.
# Equipment and Spells are shown as disabled placeholders until those
# systems ship; the entry list is the single source of truth so new
# entries (Recipe Book, Transport) only need appending.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.color_constants import C_BG, C_TEXT, C_TEXT_MUT, C_TEXT_DIM
from engine.io.save_manager import GameStateManager
from engine.title.save_modal_scene import SaveModalScene


KIND_SCENE_SWITCH = "scene_switch"   # switch to a registered scene (sets return to field_menu)
KIND_OVERLAY      = "overlay"        # open a modal within this scene
KIND_DISABLED     = "disabled"       # grayed-out placeholder (feature not yet implemented)


@dataclass(frozen=True)
class MenuEntry:
    label: str
    kind: str
    target: str | None   # registry key for scene_switch, or overlay id for overlay


ROW_H            = 44
ROW_PAD_X        = 16
TITLE_OFFSET_Y   = 50
HINT_MARGIN_Y    = 40
C_ROW_SEL_BG     = (42, 42, 74)
C_ROW_SEL_BDR    = (74, 74, 122)
C_ROW_SEL_TEXT   = (255, 220, 100)


class FieldMenuScene(Scene):
    """
    Full-screen menu. Switches into sub-scenes (Items/Status) that will return
    to `field_menu`, and overlays SaveModalScene for the Save entry.
    Closes back to the world map on M / ESC.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        game_state_manager: GameStateManager,
        return_scene_name: str,
        sfx_manager,
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager

        self._entries: list[MenuEntry] = [
            MenuEntry("Items",     KIND_SCENE_SWITCH, "items"),
            MenuEntry("Status",    KIND_SCENE_SWITCH, "status"),
            MenuEntry("Equipment", KIND_SCENE_SWITCH, "equip"),
            MenuEntry("Spells",    KIND_DISABLED,     None),
            MenuEntry("Save",      KIND_OVERLAY,      "save"),
        ]
        self._selected = 0
        self._save_modal: SaveModalScene | None = None
        self._fonts_ready = False

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(32, bold=True)
        self._font_entry = f.get(24)
        self._font_hint  = f.get(16)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._save_modal:
            self._save_modal.handle_events(events)
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_m, pygame.K_ESCAPE):
                self._close()
            elif event.key == pygame.K_UP:
                self._move(-1)
            elif event.key == pygame.K_DOWN:
                self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._select()

    def _move(self, delta: int) -> None:
        total = len(self._entries)
        new = (self._selected + delta) % total
        if new != self._selected and self._sfx_manager:
            self._sfx_manager.play("hover")
        self._selected = new

    def _select(self) -> None:
        entry = self._entries[self._selected]
        if entry.kind == KIND_DISABLED:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            return
        if self._sfx_manager:
            self._sfx_manager.play("confirm")
        if entry.kind == KIND_SCENE_SWITCH:
            scene = self._registry.get(entry.target)
            setter: Callable[[str], None] | None = getattr(scene, "set_return_scene", None)
            if setter is not None:
                setter("field_menu")
            self._scene_manager.switch(scene)
        elif entry.kind == KIND_OVERLAY and entry.target == "save":
            self._open_save_modal()

    def _open_save_modal(self) -> None:
        self._save_modal = SaveModalScene(
            game_state_manager=self._game_state_manager,
            state=self._holder.get(),
            on_close=self._close_save_modal,
            sfx_manager=self._sfx_manager,
        )

    def _close_save_modal(self) -> None:
        self._save_modal = None

    def _close(self) -> None:
        if self._sfx_manager:
            self._sfx_manager.play("cancel")
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._save_modal:
            self._save_modal.update(delta)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(C_BG)
        sw, sh = screen.get_size()

        title = self._font_title.render("MENU", True, C_TEXT)
        screen.blit(title, ((sw - title.get_width()) // 2, TITLE_OFFSET_Y))

        total_h = ROW_H * len(self._entries)
        top = (sh - total_h) // 2
        for i, entry in enumerate(self._entries):
            y = top + i * ROW_H
            selected = (i == self._selected)
            self._render_row(screen, entry, y, sw, selected)

        hint = self._font_hint.render(
            "UP/DOWN select    ENTER confirm    M/ESC close",
            True, C_TEXT_DIM,
        )
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - HINT_MARGIN_Y))

        if self._save_modal:
            self._save_modal.render(screen)

    def _render_row(
        self,
        screen: pygame.Surface,
        entry: MenuEntry,
        y: int,
        sw: int,
        selected: bool,
    ) -> None:
        if entry.kind == KIND_DISABLED:
            color = C_TEXT_DIM
        elif selected:
            color = C_ROW_SEL_TEXT
        else:
            color = C_TEXT_MUT

        text = self._font_entry.render(entry.label, True, color)
        x = (sw - text.get_width()) // 2

        if selected and entry.kind != KIND_DISABLED:
            rect = (x - ROW_PAD_X, y - 4, text.get_width() + ROW_PAD_X * 2, ROW_H - 4)
            pygame.draw.rect(screen, C_ROW_SEL_BG, rect)
            pygame.draw.rect(screen, C_ROW_SEL_BDR, rect, 2)

        screen.blit(text, (x, y))
