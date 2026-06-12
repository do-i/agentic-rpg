# engine/common/warp_select_overlay.py
#
# Modal destination picker for Aric's Teleport skill. Mirrors the look of
# TargetSelectOverlay but lists warp destinations (visited locations) instead
# of party members.

from __future__ import annotations

import pygame

from engine.common.font_provider import get_fonts
from engine.world.warp_logic import WarpDestination

# ── Colors ────────────────────────────────────────────────────
C_BG       = (20, 20, 42)
C_BORDER   = (160, 140, 220)
C_HEADER   = (212, 200, 138)
C_SEL_BG   = (45, 42, 80)
C_SEL_BDR  = (180, 160, 255)
C_NORM_BDR = (55, 55, 78)
C_ROW_BG   = (28, 28, 52)
C_TEXT     = (238, 238, 238)
C_MUTED    = (130, 130, 145)
C_DIM      = (75, 75, 85)
C_HINT     = (100, 100, 118)

# ── Layout ────────────────────────────────────────────────────
MODAL_W  = 520
ROW_H    = 40
ROW_GAP  = 4
PAD      = 20
HEADER_H = 44
FOOTER_H = 30
MAX_ROWS = 8   # scroll window height


class WarpSelectOverlay:
    """Reusable destination picker rendered as a modal overlay.

    Usage:
        overlay = WarpSelectOverlay(
            destinations=warp_destinations(state.map, scenario_path),
            on_confirm=lambda dest: ...,
            on_cancel=lambda: ...,
            sfx_manager=sfx,
        )
        # each frame: overlay.handle_events(events); overlay.render(screen)
    """

    def __init__(
        self,
        destinations: list[WarpDestination],
        on_confirm: callable,
        on_cancel: callable,
        *,
        sfx_manager,
    ) -> None:
        self._destinations = destinations
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._sfx_manager = sfx_manager
        self._sel = 0
        self._fonts_ready = False

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(18, bold=True)
        self._font_name  = f.get(16, bold=True)
        self._font_meta  = f.get(13)
        self._font_hint  = f.get(14)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        count = max(len(self._destinations), 1)
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self._move(-1, count)
            elif event.key == pygame.K_DOWN:
                self._move(1, count)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._destinations:
                    self._sfx_manager.play("confirm")
                    self._on_confirm(self._destinations[self._sel])
            elif event.key == pygame.K_ESCAPE:
                self._sfx_manager.play("cancel")
                self._on_cancel()

    def _move(self, delta: int, count: int) -> None:
        old = self._sel
        self._sel = (self._sel + delta) % count
        if self._sel != old:
            self._sfx_manager.play("hover")

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        visible = min(max(len(self._destinations), 1), MAX_ROWS)
        body_h = visible * (ROW_H + ROW_GAP) + 8
        mh = HEADER_H + body_h + FOOTER_H + PAD * 2
        mx = (screen.get_width() - MODAL_W) // 2
        my = (screen.get_height() - mh) // 2

        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        pygame.draw.rect(screen, C_BG, (mx, my, MODAL_W, mh), border_radius=8)
        pygame.draw.rect(screen, C_BORDER, (mx, my, MODAL_W, mh), 1, border_radius=8)

        title = self._font_title.render("Teleport  -  Select Destination", True, C_HEADER)
        screen.blit(title, (mx + PAD, my + (HEADER_H - title.get_height()) // 2))
        pygame.draw.line(screen, C_NORM_BDR,
                         (mx + 8, my + HEADER_H), (mx + MODAL_W - 8, my + HEADER_H))

        row_y = my + HEADER_H + PAD // 2
        if not self._destinations:
            msg = self._font_hint.render("No visited destinations yet.", True, C_DIM)
            screen.blit(msg, (mx + PAD, row_y + 10))
        else:
            start = self._scroll_start(visible)
            for i in range(start, min(start + visible, len(self._destinations))):
                self._draw_row(screen, self._destinations[i], mx, row_y, i == self._sel)
                row_y += ROW_H + ROW_GAP

        footer_y = my + mh - FOOTER_H - PAD // 2
        pygame.draw.line(screen, C_NORM_BDR,
                         (mx + 8, footer_y), (mx + MODAL_W - 8, footer_y))
        hint = self._font_hint.render(
            "select · ENTER confirm · ESC cancel", True, C_HINT)
        screen.blit(hint, (mx + PAD, footer_y + 8))

    def _scroll_start(self, visible: int) -> int:
        if self._sel < visible:
            return 0
        return min(self._sel - visible + 1, len(self._destinations) - visible)

    def _draw_row(self, screen, dest: WarpDestination, mx: int, y: int, selected: bool) -> None:
        rx, rw = mx + 8, MODAL_W - 16
        bg = C_SEL_BG if selected else C_ROW_BG
        bdr = C_SEL_BDR if selected else C_NORM_BDR
        pygame.draw.rect(screen, bg, (rx, y, rw, ROW_H), border_radius=4)
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H), 1, border_radius=4)
        name = self._font_name.render(dest.name, True, C_TEXT)
        screen.blit(name, (rx + 14, y + (ROW_H - name.get_height()) // 2))
