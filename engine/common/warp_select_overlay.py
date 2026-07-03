# engine/common/warp_select_overlay.py
#
# Modal destination picker for Aric's Teleport skill. Mirrors the field-menu
# look and feel (themed panel + icon rows) but lists warp destinations
# (visited locations) instead of party members.

from __future__ import annotations

import pygame

from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.ui.theme import DIM, GOLD, INK, MUTED
from engine.common.ui.chrome import render_hint, render_icon_row, render_modal
from engine.world.warp_logic import CATEGORY_TOWN, WarpDestination

# ── Layout ────────────────────────────────────────────────────
MODAL_W   = 520
ROW_H     = 46
ROW_GAP   = 8
PAD       = 20
HEADER_H  = 52
FOOTER_H  = 34
GROUP_H   = 28   # height of a "Towns" / "World Map" section label
MAX_ROWS  = 8    # scroll window height (destination rows)

_GROUP_LABELS = {CATEGORY_TOWN: "Towns", "world": "World Map"}


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
        self._font_title = f.get(20, bold=True)
        self._font_name  = f.get(18, bold=True)
        self._font_meta  = f.get(CAPTION)
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
        start = self._scroll_start(visible)
        window = range(start, min(start + visible, len(self._destinations)))

        # Reserve vertical space for each section label shown in the window.
        group_count = self._visible_group_count(window)
        body_h = visible * (ROW_H + ROW_GAP) + group_count * GROUP_H
        mh = HEADER_H + body_h + FOOTER_H + PAD

        modal = render_modal(
            screen, MODAL_W, mh,
            title="Teleport  ·  Select Destination",
            title_font=self._font_title,
        )

        row_x = modal.x + 16
        row_w = MODAL_W - 32
        row_y = modal.y + HEADER_H
        if not self._destinations:
            render_hint(screen, self._font_hint, "No visited destinations yet.",
                        row_x + 4, row_y + 8)
        else:
            prev_category: str | None = None
            for i in window:
                dest = self._destinations[i]
                if dest.category != prev_category:
                    self._draw_group_label(screen, row_x + 4, row_y, dest.category)
                    row_y += GROUP_H
                    prev_category = dest.category
                rect = pygame.Rect(row_x, row_y, row_w, ROW_H)
                render_icon_row(
                    screen, self._font_name, rect, dest.name,
                    icon_key=f"warp_{dest.name}",
                    focused=(i == self._sel),
                    dimmed_sel=False,
                    color=INK if i == self._sel else MUTED,
                )
                row_y += ROW_H + ROW_GAP

        hint_y = modal.bottom - FOOTER_H + 6
        render_hint(screen, self._font_hint,
                    "UP/DOWN select   ·   ENTER confirm   ·   ESC cancel",
                    row_x + 4, hint_y, color=DIM)

    def _draw_group_label(
        self, screen: pygame.Surface, x: int, y: int, category: str,
    ) -> None:
        label = _GROUP_LABELS.get(category, category.title())
        screen.blit(self._font_meta.render(label.upper(), True, GOLD), (x, y + 4))

    def _visible_group_count(self, window: range) -> int:
        """Number of distinct category labels drawn in the visible window."""
        seen: list[str] = []
        prev: str | None = None
        for i in window:
            category = self._destinations[i].category
            if category != prev:
                seen.append(category)
                prev = category
        return len(seen)

    def _scroll_start(self, visible: int) -> int:
        if self._sel < visible:
            return 0
        return min(self._sel - visible + 1, len(self._destinations) - visible)
