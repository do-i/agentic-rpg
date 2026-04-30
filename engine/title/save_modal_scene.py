# engine/scenes/save_modal_scene.py

from __future__ import annotations

import pygame
from engine.common.scene.scene import Scene
from engine.common.font_provider import get_fonts
from engine.io.save_manager import GameStateManager
from engine.common.game_state import GameState
from engine.common.save_slot_data import SaveSlot

MODAL_W       = 700
MODAL_H       = 560
SLOT_HEIGHT   = 64
VISIBLE_SLOTS = 6

AUTOSAVE_ROW_Y = 55           # y offset of pinned autosave row inside modal
DIVIDER_Y      = AUTOSAVE_ROW_Y + SLOT_HEIGHT + 5
PLAYER_ROW_Y   = DIVIDER_Y + 10

POPUP_W = 320


class SaveModalScene(Scene):
    """
    Overlay save modal — does NOT replace the current scene.
    Caller renders world map underneath, then calls this render on top.

    Usage:
        modal = SaveModalScene(game_state_manager, game_state, on_close)
        # each frame: modal.update(delta); modal.render(screen)
    """

    def __init__(
        self,
        game_state_manager: GameStateManager,
        state: GameState,
        on_close: callable,
        sfx_manager=None,
    ) -> None:
        self._game_state_manager = game_state_manager
        self._state = state
        self._on_close = on_close
        self._sfx_manager = sfx_manager

        self._slots: list[SaveSlot] = []
        self._selected = 1          # start at first player slot
        self._scroll_offset = 0
        self._confirm_pending: SaveSlot | None = None
        self._popup_text: str = ""
        self._popup_active: bool = False
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title  = f.get(28, bold=True)
        self._font_slot   = f.get(22)
        self._font_small  = f.get(17)
        self._font_hint   = f.get(18)
        self._font_toast  = f.get(26, bold=True)
        self._fonts_ready = True
        self._slots = self._game_state_manager.list_slots()

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self._popup_active:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._on_close()
                return

            if self._confirm_pending:
                self._handle_confirm_events(event)
                return

            if event.key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_close()
            elif event.key == pygame.K_UP:
                self._move_selection(-1)
            elif event.key == pygame.K_DOWN:
                self._move_selection(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._select()

    def _handle_confirm_events(self, event: pygame.event.EventType) -> None:
        if event.key in (pygame.K_RETURN, pygame.K_y):
            if self._sfx_manager:
                self._sfx_manager.play("confirm")
            self._do_save(self._confirm_pending)
            self._confirm_pending = None
        elif event.key in (pygame.K_ESCAPE, pygame.K_n):
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._confirm_pending = None

    def _move_selection(self, delta: int) -> None:
        total = len(self._slots)
        new = max(1, min(self._selected + delta, total - 1))
        if new != self._selected and self._sfx_manager:
            self._sfx_manager.play("hover")
        self._selected = new
        self._clamp_scroll()

    def _clamp_scroll(self) -> None:
        rel = self._selected - 1
        if rel < self._scroll_offset:
            self._scroll_offset = rel
        elif rel >= self._scroll_offset + VISIBLE_SLOTS:
            self._scroll_offset = rel - VISIBLE_SLOTS + 1

    def _select(self) -> None:
        slot = self._slots[self._selected]
        if not slot.is_empty:
            self._confirm_pending = slot
        else:
            self._do_save(slot)

    def _do_save(self, slot: SaveSlot) -> None:
        self._game_state_manager.save(
            self._state,
            slot_index=slot.slot_index,
            overwrite_path=slot.path,
        )
        self._slots = self._game_state_manager.list_slots()
        self._popup_text = "Game Saved!"
        self._popup_active = True

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - MODAL_H) // 2
        pygame.draw.rect(screen, (20, 20, 45),    (mx, my, MODAL_W, MODAL_H))
        pygame.draw.rect(screen, (160, 160, 100), (mx, my, MODAL_W, MODAL_H), 2)

        title = self._font_title.render("SAVE GAME", True, (220, 220, 180))
        screen.blit(title, (mx + 20, my + 14))

        # Pinned autosave row
        self._render_slot_row(screen, self._slots[0], mx, my + AUTOSAVE_ROW_Y,
                              selected=False, pinned=True)

        pygame.draw.line(screen, (80, 80, 60),
                         (mx + 10, my + DIVIDER_Y), (mx + MODAL_W - 10, my + DIVIDER_Y))

        # Player slots
        for i in range(VISIBLE_SLOTS):
            slot_idx = 1 + self._scroll_offset + i
            if slot_idx >= len(self._slots):
                break
            slot = self._slots[slot_idx]
            row_y = my + PLAYER_ROW_Y + i * SLOT_HEIGHT
            self._render_slot_row(screen, slot, mx, row_y,
                                  selected=(slot_idx == self._selected))

        # Scroll arrows
        if self._scroll_offset > 0:
            up = self._font_hint.render(" ", True, (140, 140, 100))
            screen.blit(up, (mx + MODAL_W - 30, my + PLAYER_ROW_Y - 2))
        if self._scroll_offset + VISIBLE_SLOTS < len(self._slots) - 1:
            dn = self._font_hint.render(" ", True, (140, 140, 100))
            screen.blit(dn, (mx + MODAL_W - 30, my + MODAL_H - 40))

        hint = self._font_hint.render("ENTER - Save    ESC - Cancel", True, (120, 120, 90))
        screen.blit(hint, (mx + 20, my + MODAL_H - 28))

        if self._confirm_pending:
            self._render_confirm(screen, mx, my)

        if self._popup_active:
            self._render_popup(screen)

    def _render_slot_row(
        self,
        screen: pygame.Surface,
        slot: SaveSlot,
        mx: int,
        y: int,
        selected: bool,
        pinned: bool = False,
    ) -> None:
        row1_y = y + 8
        row2_y = y + 34

        bg = (38, 38, 68) if selected else (24, 24, 44)
        pygame.draw.rect(screen, bg, (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4))

        if selected:
            pygame.draw.rect(screen, (240, 200, 60),
                             (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4), 2)

        label_col = (140, 140, 110) if pinned else (200, 200, 160) if not slot.is_empty else (80, 80, 70)
        label = self._font_slot.render(slot.label, True, label_col)
        screen.blit(label, (mx + 12, row1_y))

        if slot.is_empty:
            empty = self._font_slot.render("--- Empty ---", True, (70, 70, 60))
            screen.blit(empty, (mx + 110, row1_y))
            return

        lv = self._font_small.render(f"Lv {slot.level}", True, (160, 160, 130))
        screen.blit(lv, (mx + 12, row2_y))

        # Row 1: Location  (Name)
        loc = self._font_slot.render(slot.location, True, (240, 240, 200))
        screen.blit(loc, (mx + 110, row1_y))
        name = self._font_small.render(f"({slot.protagonist_name})", True, (140, 140, 110))
        screen.blit(name, (mx + 110 + loc.get_width() + 10, row1_y + 4))

        # Row 2: Timestamp  Playtime
        ts = self._font_small.render(slot.timestamp, True, (140, 140, 110))
        screen.blit(ts, (mx + 110, row2_y))
        pt = self._font_small.render(slot.playtime_display, True, (140, 140, 110))
        screen.blit(pt, (mx + 310, row2_y))

    def _render_confirm(self, screen: pygame.Surface, mx: int, my: int) -> None:
        bw, bh = 420, 110
        bx = mx + (MODAL_W - bw) // 2
        by = my + (MODAL_H - bh) // 2
        pygame.draw.rect(screen, (30, 15, 15), (bx, by, bw, bh))
        pygame.draw.rect(screen, (200, 80, 80), (bx, by, bw, bh), 2)
        msg = self._font_slot.render("Overwrite this save?", True, (220, 180, 180))
        screen.blit(msg, (bx + 20, by + 18))
        hint = self._font_hint.render("ENTER / Y - Confirm    ESC / N - Cancel", True, (160, 120, 120))
        screen.blit(hint, (bx + 20, by + 60))

    def _render_popup(self, screen: pygame.Surface) -> None:
        ph = 80
        px = (screen.get_width()  - POPUP_W) // 2
        py = (screen.get_height() - ph) // 2
        pygame.draw.rect(screen, (20, 20, 45),    (px, py, POPUP_W, ph), border_radius=6)
        pygame.draw.rect(screen, (160, 160, 100), (px, py, POPUP_W, ph), 2, border_radius=6)
        msg = self._font_toast.render(self._popup_text, True, (100, 220, 100))
        screen.blit(msg, (px + (POPUP_W - msg.get_width()) // 2, py + 14))
        hint = self._font_hint.render("ENTER / ESC  close", True, (120, 120, 90))
        screen.blit(hint, (px + (POPUP_W - hint.get_width()) // 2, py + ph - 28))
