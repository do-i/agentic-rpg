# engine/common/item_selection_view.py
#
# Reusable scrollable item selection list used by shops, apothecary, and the
# party item screen.  Owns row layout, cursor, scrolling math, and an overflow
# hint rendered as a partial last row with a vertical alpha fade.

from __future__ import annotations

from dataclasses import dataclass

import pygame

from engine.common.font_provider import get_fonts


@dataclass
class ItemRow:
    title: str
    subtitle: str | None = None
    icon: pygame.Surface | None = None
    right_text: str | None = None
    locked: bool = False
    badge: str | None = None
    badge_color: tuple[int, int, int] | None = None


@dataclass
class ItemSelectionTheme:
    sel_bg:      tuple[int, int, int] = (50, 50, 85)
    sel_bdr:     tuple[int, int, int] = (212, 200, 138)
    norm_bdr:    tuple[int, int, int] = (45, 45, 68)
    row_bg:      tuple[int, int, int] = (30, 30, 50)
    cursor:      tuple[int, int, int] = (212, 200, 138)
    title_sel:   tuple[int, int, int] = (238, 238, 238)
    title_norm:  tuple[int, int, int] = (170, 170, 170)
    title_lock:  tuple[int, int, int] = (90, 90, 100)
    subtitle:    tuple[int, int, int] = (130, 130, 140)
    subtitle_lk: tuple[int, int, int] = (90, 90, 100)
    right:       tuple[int, int, int] = (200, 185, 100)
    right_lock:  tuple[int, int, int] = (80, 80, 90)


class ItemSelectionView:
    """Stateless renderer for scrollable selectable item lists."""

    PEEK_RATIO   = 0.40   # fraction of an extra row shown when more rows exist
    ROW_INSET_X  = 10     # margin from rect edge
    CURSOR_X     = 8      # cursor x relative to row left
    CONTENT_X    = 28     # left edge of icon/title relative to row left
    RIGHT_PAD    = 16

    def __init__(
        self,
        theme: ItemSelectionTheme | None = None,
        row_h: int = 44,
        row_gap: int = 4,
        font_size: int = 16,
        sub_font_size: int = 13,
    ) -> None:
        self._theme = theme or ItemSelectionTheme()
        self.row_h = row_h
        self.row_gap = row_gap
        self._font_size = font_size
        self._sub_font_size = sub_font_size
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title  = f.get(self._font_size)
        self._font_sub    = f.get(self._sub_font_size)
        self._font_right  = f.get(self._font_size)
        self._font_cursor = f.get(self._font_size + 4)
        self._font_badge  = f.get(11, bold=True)
        self._fonts_ready = True

    # ── Public layout helpers ─────────────────────────────────

    def compute_visible_rows(self, rect_height: int) -> int:
        """How many full rows fit in the given height."""
        step = self.row_h + self.row_gap
        return max(1, rect_height // step)

    def list_height(self, full_rows: int, has_overflow: bool) -> int:
        """Pixel height to draw `full_rows` plus optional partial peek row."""
        step = self.row_h + self.row_gap
        peek = int(self.row_h * self.PEEK_RATIO) if has_overflow else 0
        return full_rows * step + peek

    # ── Selection / scroll math ───────────────────────────────

    @classmethod
    def move_selection(
        cls,
        delta: int,
        sel: int,
        scroll: int,
        total: int,
        visible_rows: int,
    ) -> tuple[int, int]:
        """Return (new_sel, new_scroll) after moving selection by `delta`."""
        if total <= 0:
            return 0, 0
        new_sel = max(0, min(total - 1, sel + delta))
        new_scroll = scroll
        if new_sel < new_scroll:
            new_scroll = new_sel
        elif new_sel >= new_scroll + visible_rows:
            new_scroll = new_sel - visible_rows + 1
        new_scroll = max(0, min(new_scroll, max(0, total - visible_rows)))
        return new_sel, new_scroll

    @classmethod
    def clamp_scroll(cls, sel: int, scroll: int, total: int, visible_rows: int) -> int:
        if total <= 0:
            return 0
        if sel < scroll:
            scroll = sel
        elif sel >= scroll + visible_rows:
            scroll = sel - visible_rows + 1
        return max(0, min(scroll, max(0, total - visible_rows)))

    # ── Render ────────────────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        rows: list[ItemRow],
        sel: int,
        scroll: int,
        active: bool = True,
    ) -> None:
        """Draw the list inside `rect`. Cursor only when `active`."""
        if not self._fonts_ready:
            self._init_fonts()

        if not rows:
            return

        visible = self.compute_visible_rows(rect.height)
        rx = rect.x + self.ROW_INSET_X
        rw = rect.width - 2 * self.ROW_INSET_X
        step = self.row_h + self.row_gap

        for i in range(visible):
            idx = scroll + i
            if idx >= len(rows):
                return
            row_y = rect.y + i * step
            self._draw_row(
                screen, rows[idx], rx, row_y, rw, self.row_h,
                selected=(idx == sel and active),
            )

        peek_idx = scroll + visible
        if peek_idx < len(rows):
            self._draw_peek_row(
                screen, rows[peek_idx], rx, rect.y + visible * step, rw,
                selected=(peek_idx == sel and active),
            )

    # ── Row drawing ──────────────────────────────────────────

    def _draw_row(
        self,
        screen: pygame.Surface,
        row: ItemRow,
        rx: int, ry: int, rw: int, rh: int,
        selected: bool,
    ) -> None:
        t = self._theme
        bg  = t.sel_bg  if selected else t.row_bg
        bdr = t.sel_bdr if selected else t.norm_bdr
        pygame.draw.rect(screen, bg,  (rx, ry, rw, rh), border_radius=4)
        pygame.draw.rect(screen, bdr, (rx, ry, rw, rh), 1, border_radius=4)

        if selected:
            cur = self._font_cursor.render(" ", True, t.cursor)
            screen.blit(cur, (rx + self.CURSOR_X, ry + (rh - cur.get_height()) // 2))

        content_x = rx + self.CONTENT_X

        if row.icon is not None:
            icon = row.icon
            iy = ry + (rh - icon.get_height()) // 2
            screen.blit(icon, (content_x, iy))
            content_x += icon.get_width() + 8

        title_y = ry + 6 if row.subtitle else ry + (rh - self._font_title.get_height()) // 2

        text_x = content_x
        if row.badge:
            badge_color = row.badge_color or t.cursor
            bsurf = self._font_badge.render(row.badge, True, badge_color)
            badge_y = ry + (rh - bsurf.get_height()) // 2 if not row.subtitle else title_y + 2
            screen.blit(bsurf, (text_x, badge_y))
            text_x += bsurf.get_width() + 6

        if row.locked:
            tcol = t.title_lock
        elif selected:
            tcol = t.title_sel
        else:
            tcol = t.title_norm
        tsurf = self._font_title.render(row.title, True, tcol)
        screen.blit(tsurf, (text_x, title_y))

        if row.subtitle:
            scol = t.subtitle_lk if row.locked else t.subtitle
            ssurf = self._font_sub.render(row.subtitle, True, scol)
            screen.blit(ssurf, (content_x, ry + rh - ssurf.get_height() - 4))

        if row.right_text:
            rcol = t.right_lock if row.locked else t.right
            rsurf = self._font_right.render(row.right_text, True, rcol)
            screen.blit(
                rsurf,
                (rx + rw - rsurf.get_width() - self.RIGHT_PAD,
                 ry + (rh - rsurf.get_height()) // 2),
            )

    def _draw_peek_row(
        self,
        screen: pygame.Surface,
        row: ItemRow,
        rx: int, ry: int, rw: int,
        selected: bool,
    ) -> None:
        """Draw partial last row (top-clipped, vertical alpha fade)."""
        peek_h = int(self.row_h * self.PEEK_RATIO)
        if peek_h <= 0:
            return

        # Render the row in full into an offscreen surface, then take the top
        # `peek_h` pixels and multiply by a top→bottom alpha fade.
        full = pygame.Surface((rw, self.row_h), pygame.SRCALPHA)
        self._draw_row(full, row, 0, 0, rw, self.row_h, selected=selected)

        peek = full.subsurface(pygame.Rect(0, 0, rw, peek_h)).copy()
        gradient = pygame.Surface((rw, peek_h), pygame.SRCALPHA)
        for y in range(peek_h):
            alpha = int(255 * (1.0 - y / peek_h))
            gradient.fill((255, 255, 255, alpha), pygame.Rect(0, y, rw, 1))
        peek.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        screen.blit(peek, (rx, ry))
