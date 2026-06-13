# engine/field_menu/field_menu_scene.py
#
# Pause / field menu — opened from the world map (M key).
# Lists party-wide actions: Items, Status, Equipment, Spells, Save.
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
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    TEAL,
    draw_divider,
    draw_stat_bar,
    member_icon_path,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
)
from engine.common.menu_sfx_mixin import MenuSfxMixin
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
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager

        self._entries: list[MenuEntry] = [
            MenuEntry("Items",     KIND_SCENE_SWITCH, "items",  "satchel", "use, sort, and inspect supplies"),
            MenuEntry("Status",    KIND_SCENE_SWITCH, "status", "pulse",   "review health, rows, and growth"),
            MenuEntry("Equipment", KIND_SCENE_SWITCH, "equip",  "blade",   "tune gear and compare stats"),
            MenuEntry("Spells",    KIND_SCENE_SWITCH, "spells", "sigil",   "cast field magic and utilities"),
            MenuEntry("Save",      KIND_OVERLAY,      "save",   "seal",    "record the current journey"),
        ]
        self._selected = 0
        self._save_modal: SaveModalScene | None = None
        self._fonts_ready = False

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(32, bold=True)
        self._font_entry = f.get(22, bold=True)
        self._font_meta  = f.get(14)
        self._font_hint  = f.get(15)
        self._font_panel = f.get(18, bold=True)
        self._font_small = f.get(13)
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
        self._play("cancel")
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._save_modal:
            self._save_modal.update(delta)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        sw, sh = screen.get_size()
        render_backdrop(screen)
        render_header(screen, self._font_title, self._font_hint, "FIELD MENU", MENU_SUBTITLE, 52, 34)

        menu_w = min(460, max(340, int(sw * 0.38)))
        menu_rect = pygame.Rect(48, 122, menu_w, min(430, sh - 190))
        party_rect = pygame.Rect(menu_rect.right + 28, 122, sw - menu_rect.right - 76, menu_rect.h)
        if party_rect.w < 360:
            party_rect = pygame.Rect(48, menu_rect.bottom + 18, sw - 96, max(150, sh - menu_rect.bottom - 76))

        render_panel(screen, menu_rect, active=True, title="Commands", title_font=self._font_panel)
        self._render_commands(screen, menu_rect)

        render_panel(screen, party_rect, title="Party Readout", title_font=self._font_panel)
        self._render_party_readout(screen, party_rect)

        hint = self._font_hint.render(
            "UP/DOWN select    ENTER confirm    M/ESC close",
            True, C_TEXT_DIM,
        )
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - HINT_MARGIN_Y))

        if self._save_modal:
            self._save_modal.render(screen)

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

    def _render_party_readout(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        members = list(self._holder.get().party.members)
        x = panel.x + 20
        y = panel.y + 54
        w = panel.w - 40
        if not members:
            msg = self._font_entry.render("No party members.", True, DIM)
            screen.blit(msg, (x, y))
            return

        row_h = min(62, max(50, (panel.bottom - y - 22) // max(1, len(members))))
        for i, member in enumerate(members[:5]):
            row = pygame.Rect(x, y + i * row_h, w, row_h - 8)
            render_icon_row(
                screen,
                self._font_entry,
                row,
                f"{member.name}  Lv{member.level}",
                icon_key=f"member_{member.id}",
                image_path=member_icon_path(member.id),
                focused=i == 0,
                dimmed_sel=False,
                color=INK,
                right_text=member.class_name.title(),
                right_font=self._font_meta,
                subtext=f"HP {member.hp}/{member.hp_max}    MP {member.mp}/{member.mp_max}",
                sub_font=self._font_small,
            )
            bar_y = row.bottom - 9
            draw_stat_bar(screen, pygame.Rect(row.x + 56, bar_y, max(60, row.w // 4), 5), member.hp, member.hp_max, (132, 196, 111))
            draw_stat_bar(screen, pygame.Rect(row.x + 64 + max(60, row.w // 4), bar_y, max(60, row.w // 4), 5), member.mp, member.mp_max, TEAL)

        draw_divider(screen, x, panel.bottom - 50, w)
        playtime = self._holder.get().playtime.display
        footer = self._font_small.render(f"Playtime {playtime}", True, GOLD)
        screen.blit(footer, (x, panel.bottom - 38))
