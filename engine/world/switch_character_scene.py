# engine/world/switch_character_scene.py

from __future__ import annotations

import pygame
from pathlib import Path

from engine.common.scene.scene import Scene
from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.game_state_holder import GameStateHolder
from engine.common.menu_sfx_mixin import MenuSfxMixin
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    fit_text,
    render_hint,
    render_modal,
    render_row_frame,
)
from engine.world.sprite_sheet import Direction
from engine.world.sprite_sheet_cache import SpriteSheetCache
from engine.world.world_map_init import load_party_member_sprite

MODAL_W = 460
ROW_H = 54
ROW_GAP = 8
TITLE_H = 52
HINT_H = 34
PAD = 18
SPRITE_SIZE = 40


class SwitchCharacterScene(MenuSfxMixin, Scene):
    """Overlay for switching the visible player sprite to any party member."""

    def __init__(
        self,
        holder: GameStateHolder,
        sprite_cache: SpriteSheetCache,
        scenario_path: Path,
        on_close: callable,
        sfx_manager,
    ) -> None:
        self._holder = holder
        self._sprite_cache = sprite_cache
        self._scenario_path = scenario_path
        self._on_close = on_close
        self._sfx_manager = sfx_manager

        state = holder.get()
        self._party = state.party
        self._members = self._party.members
        self._controlled_id = state.controlled_member_id or (
            self._party.protagonist.id if self._party.protagonist else ""
        )
        self._selected = self._get_selected_index()
        self._fonts_ready = False
        # member id -> idle DOWN frame scaled to SPRITE_SIZE (None when no sheet)
        self._sprite_frames: dict[str, pygame.Surface | None] = {}

    def _get_selected_index(self) -> int:
        for i, member in enumerate(self._members):
            if member.id == self._controlled_id:
                return i
        return 0

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(18, bold=True)
        self._font_row = f.get(20, bold=True)
        self._font_meta = f.get(CAPTION)
        self._font_hint = f.get(15)
        self._fonts_ready = True

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self._move(-1)
            elif event.key == pygame.K_DOWN:
                self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._confirm_selection()
            elif event.key == pygame.K_ESCAPE:
                self._play("cancel")
                self._on_close()

    def _move(self, delta: int) -> None:
        total = len(self._members)
        self._selected = self._set_sel_hover(
            self._selected, (self._selected + delta) % total
        )

    def _confirm_selection(self) -> None:
        if self._selected < len(self._members):
            member = self._members[self._selected]
            state = self._holder.get()
            state.controlled_member_id = member.id
            self._controlled_id = member.id
            self._play("confirm")
        self._on_close()

    def _member_frame(self, member_id: str) -> pygame.Surface | None:
        if member_id not in self._sprite_frames:
            sheet = load_party_member_sprite(
                member_id, self._scenario_path, self._sprite_cache
            )
            self._sprite_frames[member_id] = (
                sheet.get_scaled_frame(
                    Direction.DOWN, 0, (SPRITE_SIZE, SPRITE_SIZE)
                )
                if sheet is not None
                else None
            )
        return self._sprite_frames[member_id]

    def update(self, delta: float) -> None:
        pass

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        rows_h = len(self._members) * ROW_H + max(0, len(self._members) - 1) * ROW_GAP
        modal_h = TITLE_H + rows_h + HINT_H + PAD * 2
        modal = render_modal(
            screen,
            MODAL_W,
            modal_h,
            title="Switch Character",
            title_font=self._font_title,
        )

        x = modal.x + PAD
        w = modal.w - PAD * 2
        row_y = modal.y + TITLE_H
        for i, member in enumerate(self._members):
            focused = i == self._selected
            is_active = member.id == self._controlled_id
            rect = pygame.Rect(x, row_y + i * (ROW_H + ROW_GAP), w, ROW_H)
            self._render_member_row(screen, rect, member, focused, is_active)

        hint_y = modal.bottom - HINT_H + 6
        render_hint(
            screen,
            self._font_hint,
            "UP/DOWN select    ENTER confirm    ESC cancel",
            modal.x + PAD,
            hint_y,
        )

    def _render_member_row(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        member,
        focused: bool,
        is_active: bool,
    ) -> None:
        render_row_frame(
            screen, rect, focused=focused, dimmed_sel=is_active and not focused
        )

        sprite = self._member_frame(member.id)
        if sprite is not None:
            sprite_y = rect.y + (rect.h - SPRITE_SIZE) // 2
            screen.blit(sprite, (rect.x + 8, sprite_y))

        color = INK if focused else MUTED
        tx = rect.x + 8 + SPRITE_SIZE + 12
        max_w = rect.right - tx - 14

        badge = ""
        if is_active:
            badge = "ACTIVE"
            max_w -= self._font_meta.size(badge)[0] + 20

        label = fit_text(self._font_row, member.name, color, max_w)
        label_y = rect.y + (rect.h - label.get_height()) // 2
        screen.blit(label, (tx, label_y))

        if is_active:
            badge_s = self._font_meta.render("ACTIVE", True, GOLD if focused else DIM)
            screen.blit(
                badge_s,
                (rect.right - 14 - badge_s.get_width(),
                 rect.y + (rect.h - badge_s.get_height()) // 2),
            )
