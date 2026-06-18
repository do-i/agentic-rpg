# engine/world/switch_character_scene.py

from __future__ import annotations

import pygame
from pathlib import Path

from engine.common.scene.scene import Scene
from engine.common.font_provider import get_fonts
from engine.common.game_state_holder import GameStateHolder
from engine.common.color_constants import C_BG, C_TEXT, C_TEXT_DIM
from engine.party.party_state import PartyState
from engine.world.sprite_sheet_cache import SpriteSheetCache

MODAL_W = 480
ROW_H = 50
TITLE_H = 42
HINT_H = 32
PAD = 20


class SwitchCharacterScene(Scene):
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

    def _get_selected_index(self) -> int:
        for i, member in enumerate(self._members):
            if member.id == self._controlled_id:
                return i
        return 0

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_row = f.get(20, bold=True)
        self._font_hint = f.get(16)
        self._fonts_ready = True

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self._selected = (self._selected - 1) % len(self._members)
                self._sfx_manager.play("cursor")
            elif event.key == pygame.K_DOWN:
                self._selected = (self._selected + 1) % len(self._members)
                self._sfx_manager.play("cursor")
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._confirm_selection()
            elif event.key == pygame.K_ESCAPE:
                self._on_close()

    def _confirm_selection(self) -> None:
        if self._selected < len(self._members):
            member = self._members[self._selected]
            state = self._holder.get()
            state.controlled_member_id = member.id
            self._sfx_manager.play("select")
        self._on_close()

    def update(self, delta: float) -> None:
        pass

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        width = screen.get_width()
        height = screen.get_height()
        modal_x = (width - MODAL_W) // 2
        modal_y = (height - (TITLE_H + len(self._members) * ROW_H + HINT_H + PAD * 3)) // 2

        pygame.draw.rect(screen, C_BG, (modal_x - 2, modal_y - 2, MODAL_W + 4, TITLE_H + len(self._members) * ROW_H + HINT_H + PAD * 3 + 4))
        pygame.draw.rect(screen, (40, 40, 40), (modal_x, modal_y, MODAL_W, TITLE_H + len(self._members) * ROW_H + HINT_H + PAD * 3))

        title = self._font_title.render("Switch Character", True, C_TEXT)
        screen.blit(title, (modal_x + PAD, modal_y + PAD))

        row_y = modal_y + TITLE_H + PAD
        for i, member in enumerate(self._members):
            is_selected = i == self._selected
            color = C_TEXT if is_selected else C_TEXT_DIM
            prefix = "> " if is_selected else "  "
            label = f"{prefix}{member.name}"
            text = self._font_row.render(label, True, color)
            screen.blit(text, (modal_x + PAD, row_y + i * ROW_H))

        hint_y = modal_y + TITLE_H + len(self._members) * ROW_H + PAD * 2
        hint = self._font_hint.render("UP/DOWN Select  Enter Confirm  ESC Cancel", True, C_TEXT_DIM)
        screen.blit(hint, (modal_x + PAD, hint_y))
