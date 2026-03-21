# engine/core/scenes/save_modal_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.settings import Settings
from engine.core.state.game_state_manager import GameStateManager
from engine.core.state.game_state import GameState
from engine.core.models.save_slot import SaveSlot

MODAL_W = 700
MODAL_H = 480
SLOT_HEIGHT = 44
VISIBLE_SLOTS = 8

TOAST_DURATION = 1.8  # seconds


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
    ) -> None:
        self._game_state_manager = game_state_manager
        self._state = state
        self._on_close = on_close

        self._slots: list[SaveSlot] = []
        self._selected = 1          # start at first player slot
        self._scroll_offset = 0
        self._confirm_pending: SaveSlot | None = None   # overwrite confirm
        self._toast_text: str = ""
        self._toast_timer: float = 0.0
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 28, bold=True)
        self._font_slot   = pygame.font.SysFont("Arial", 22)
        self._font_hint   = pygame.font.SysFont("Arial", 18)
        self._font_toast  = pygame.font.SysFont("Arial", 26, bold=True)
        self._fonts_ready = True
        self._slots = self._game_state_manager.list_slots()

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self._confirm_pending:
                self._handle_confirm_events(event)
                return

            if event.key == pygame.K_ESCAPE:
                self._on_close()
            elif event.key == pygame.K_UP:
                self._move_selection(-1)
            elif event.key == pygame.K_DOWN:
                self._move_selection(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._select()

    def _handle_confirm_events(self, event: pygame.event.EventType) -> None:
        if event.key in (pygame.K_RETURN, pygame.K_y):
            self._do_save(self._confirm_pending)
            self._confirm_pending = None
        elif event.key in (pygame.K_ESCAPE, pygame.K_n):
            self._confirm_pending = None

    def _move_selection(self, delta: int) -> None:
        # skip autosave slot (index 0) — not player-selectable
        total = len(self._slots)
        new = self._selected + delta
        new = max(1, min(new, total - 1))
        self._selected = new
        self._clamp_scroll()

    def _clamp_scroll(self) -> None:
        # keep selected in visible window (slots 1+ shown, autosave pinned top)
        rel = self._selected - 1  # relative to player slots
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
        self._toast_text = "Game Saved!"
        self._toast_timer = TOAST_DURATION

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._toast_timer > 0:
            self._toast_timer -= delta
            if self._toast_timer <= 0:
                self._on_close()

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        # dim background
        overlay = pygame.Surface((Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # modal box
        mx = (Settings.SCREEN_WIDTH - MODAL_W) // 2
        my = (Settings.SCREEN_HEIGHT - MODAL_H) // 2
        pygame.draw.rect(screen, (20, 20, 45), (mx, my, MODAL_W, MODAL_H))
        pygame.draw.rect(screen, (160, 160, 100), (mx, my, MODAL_W, MODAL_H), 2)

        # title
        title = self._font_title.render("SAVE GAME", True, (220, 220, 180))
        screen.blit(title, (mx + 20, my + 14))

        # autosave row (pinned, not selectable)
        self._render_slot_row(screen, self._slots[0], mx, my + 55, selected=False, pinned=True)

        # divider
        pygame.draw.line(screen, (80, 80, 60), (mx + 10, my + 100), (mx + MODAL_W - 10, my + 100))

        # player slots
        for i in range(VISIBLE_SLOTS):
            slot_idx = 1 + self._scroll_offset + i
            if slot_idx >= len(self._slots):
                break
            slot = self._slots[slot_idx]
            row_y = my + 110 + i * SLOT_HEIGHT
            selected = (slot_idx == self._selected)
            self._render_slot_row(screen, slot, mx, row_y, selected=selected)

        # scroll hint
        if self._scroll_offset > 0:
            up = self._font_hint.render("▲", True, (140, 140, 100))
            screen.blit(up, (mx + MODAL_W - 30, my + 108))
        if self._scroll_offset + VISIBLE_SLOTS < len(self._slots) - 1:
            dn = self._font_hint.render("▼", True, (140, 140, 100))
            screen.blit(dn, (mx + MODAL_W - 30, my + MODAL_H - 40))

        # hints bar
        hint = self._font_hint.render("ENTER — Save    ESC — Cancel", True, (120, 120, 90))
        screen.blit(hint, (mx + 20, my + MODAL_H - 28))

        # overwrite confirm overlay
        if self._confirm_pending:
            self._render_confirm(screen, mx, my)

        # toast
        if self._toast_timer > 0:
            self._render_toast(screen)

    def _render_slot_row(
        self,
        screen: pygame.Surface,
        slot: SaveSlot,
        mx: int,
        y: int,
        selected: bool,
        pinned: bool = False,
    ) -> None:
        bg = (40, 40, 70) if selected else (25, 25, 45)
        pygame.draw.rect(screen, bg, (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4))

        if selected:
            cursor = self._font_slot.render("▶", True, (255, 220, 50))
            screen.blit(cursor, (mx + 14, y + 8))

        label_color = (200, 200, 160) if not pinned else (140, 140, 110)
        label = self._font_slot.render(slot.label, True, label_color)
        screen.blit(label, (mx + 38, y + 8))

        detail_color = (180, 180, 140) if selected else (140, 140, 110)
        detail = self._font_slot.render(slot.display_line(), True, detail_color)
        screen.blit(detail, (mx + 160, y + 8))

    def _render_confirm(self, screen: pygame.Surface, mx: int, my: int) -> None:
        bw, bh = 420, 110
        bx = mx + (MODAL_W - bw) // 2
        by = my + (MODAL_H - bh) // 2
        pygame.draw.rect(screen, (30, 15, 15), (bx, by, bw, bh))
        pygame.draw.rect(screen, (200, 80, 80), (bx, by, bw, bh), 2)
        msg = self._font_slot.render("Overwrite this save?", True, (220, 180, 180))
        screen.blit(msg, (bx + 20, by + 18))
        hint = self._font_hint.render("ENTER / Y — Confirm    ESC / N — Cancel", True, (160, 120, 120))
        screen.blit(hint, (bx + 20, by + 60))

    def _render_toast(self, screen: pygame.Surface) -> None:
        surf = self._font_toast.render(self._toast_text, True, (100, 220, 100))
        x = (Settings.SCREEN_WIDTH - surf.get_width()) // 2
        screen.blit(surf, (x, Settings.SCREEN_HEIGHT - 80))
