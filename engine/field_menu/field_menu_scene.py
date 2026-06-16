# engine/field_menu/field_menu_scene.py
#
# Pause / field menu — opened from the world map (M key).
# Lists party-wide actions: Status, Spells, Items, Equipment, Save, Quit.
# The entry list is the single source of truth so new entries
# (Recipe Book, Transport) only need appending.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.color_constants import C_TEXT_DIM
from engine.common.font_roles import CAPTION
from engine.common.field_menu_theme import (
    DIM,
    INK,
    MUTED,
    render_backdrop,
    render_header,
    render_icon_row,
    render_modal,
    render_panel,
)
from engine.common.menu_sfx_mixin import MenuSfxMixin
from engine.io.save_manager import GameStateManager
from engine.title.save_modal_scene import SaveModalScene
from engine.world.switch_character_scene import SwitchCharacterScene


KIND_SCENE_SWITCH = "scene_switch"   # switch to a registered scene (sets return to field_menu)
KIND_OVERLAY      = "overlay"        # open a modal within this scene
KIND_DISABLED     = "disabled"       # grayed-out placeholder (feature not yet implemented)


@dataclass(frozen=True)
class MenuEntry:
    label: str
    kind: str
    target: str | None   # registry key for scene_switch, or overlay id for overlay
    icon_key: str = "menu"
    description: str = ""


ROW_H = 58
HINT_MARGIN_Y = 32
MENU_SUBTITLE = "party command deck"


class FieldMenuScene(MenuSfxMixin, Scene):
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
        sprite_cache=None,
        scenario_path=None,
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager
        self._sprite_cache = sprite_cache
        self._scenario_path = scenario_path

        self._entries: list[MenuEntry] = [
            MenuEntry("Status",    KIND_SCENE_SWITCH, "status", "pulse",   "review health, rows, and growth"),
            MenuEntry("Spells",    KIND_SCENE_SWITCH, "spells", "sigil",   "cast field magic and utilities"),
            MenuEntry("Items",     KIND_SCENE_SWITCH, "items",  "satchel", "use, sort, and inspect supplies"),
            MenuEntry("Equipment", KIND_SCENE_SWITCH, "equip",  "blade",   "tune gear and compare stats"),
            MenuEntry("Character", KIND_OVERLAY,      "switch", "person",  "control a different party member"),
            MenuEntry("Save",      KIND_OVERLAY,      "save",   "seal",    "record the current journey"),
            MenuEntry("Quit",      KIND_OVERLAY,      "quit",   "quit",    "exit the game to desktop"),
        ]
        self._selected = 0
        self._save_modal: SaveModalScene | None = None
        self._switch_modal: SwitchCharacterScene | None = None
        self._quit_confirm: bool = False
        self._fonts_ready = False

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(32, bold=True)
        self._font_entry = f.get(22, bold=True)
        self._font_meta  = f.get(CAPTION)
        self._font_hint  = f.get(15)
        self._font_panel = f.get(18, bold=True)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._switch_modal:
            self._switch_modal.handle_events(events)
            return

        if self._save_modal:
            self._save_modal.handle_events(events)
            return

        if self._quit_confirm:
            for event in events:
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._play("confirm")
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                elif event.key == pygame.K_ESCAPE:
                    self._play("cancel")
                    self._quit_confirm = False
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
        self._selected = self._set_sel_hover(self._selected, (self._selected + delta) % total)

    def _select(self) -> None:
        entry = self._entries[self._selected]
        if entry.kind == KIND_DISABLED:
            self._play("cancel")
            return
        self._play("confirm")
        if entry.kind == KIND_SCENE_SWITCH:
            scene = self._registry.get(entry.target)
            setter: Callable[[str], None] | None = getattr(scene, "set_return_scene", None)
            if setter is not None:
                setter("field_menu")
            self._scene_manager.switch(scene)
        elif entry.kind == KIND_OVERLAY and entry.target == "switch":
            self._open_switch_modal()
        elif entry.kind == KIND_OVERLAY and entry.target == "save":
            self._open_save_modal()
        elif entry.kind == KIND_OVERLAY and entry.target == "quit":
            self._quit_confirm = True

    def _open_switch_modal(self) -> None:
        if self._sprite_cache and self._scenario_path:
            self._switch_modal = SwitchCharacterScene(
                holder=self._holder,
                sprite_cache=self._sprite_cache,
                scenario_path=self._scenario_path,
                on_close=self._close_switch_modal,
                sfx_manager=self._sfx_manager,
            )

    def _close_switch_modal(self) -> None:
        self._switch_modal = None

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
        self._play("cancel")
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._switch_modal:
            self._switch_modal.update(delta)
        if self._save_modal:
            self._save_modal.update(delta)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        sw, sh = screen.get_size()
        render_backdrop(screen)
        render_header(screen, self._font_title, self._font_hint, "FIELD MENU", MENU_SUBTITLE, 52, 34)

        menu_w = min(460, max(340, int(sw * 0.42)))
        menu_h = min(54 + len(self._entries) * (ROW_H + 8) + 18, sh - 190)
        menu_rect = pygame.Rect((sw - menu_w) // 2, 122, menu_w, menu_h)

        render_panel(screen, menu_rect, active=True, title="Commands", title_font=self._font_panel)
        self._render_commands(screen, menu_rect)

        hint = self._font_hint.render(
            "UP/DOWN select    ENTER confirm    M/ESC close",
            True, C_TEXT_DIM,
        )
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - HINT_MARGIN_Y))

        if self._switch_modal:
            self._switch_modal.render(screen)

        if self._save_modal:
            self._save_modal.render(screen)

        if self._quit_confirm:
            self._render_quit_confirm(screen)

    def _render_quit_confirm(self, screen: pygame.Surface) -> None:
        rect = render_modal(
            screen,
            360,
            150,
            title="Quit Game?",
            title_font=self._font_panel,
        )

        prompt = self._font_meta.render("Exit to desktop?", True, MUTED)
        screen.blit(prompt, (rect.centerx - prompt.get_width() // 2, rect.y + 58))

        hint = self._font_hint.render("ENTER  confirm        ESC  cancel", True, DIM)
        screen.blit(hint, (rect.centerx - hint.get_width() // 2, rect.bottom - 36))

    def _render_commands(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        x = panel.x + 18
        y = panel.y + 54
        w = panel.w - 36
        for i, entry in enumerate(self._entries):
            selected = (i == self._selected)
            if entry.kind == KIND_DISABLED:
                color = DIM
            elif selected:
                color = INK
            else:
                color = MUTED
            rect = pygame.Rect(x, y + i * (ROW_H + 8), w, ROW_H)
            render_icon_row(
                screen,
                self._font_entry,
                rect,
                entry.label,
                icon_key=entry.icon_key,
                focused=selected and entry.kind != KIND_DISABLED,
                dimmed_sel=False,
                color=color,
                subtext=entry.description,
                sub_font=self._font_meta,
            )
