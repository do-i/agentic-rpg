# engine/shop/magic_core_shop_renderer.py
#
# All rendering for the Magic Core Shop scene.

from __future__ import annotations

import pygame
from engine.common.font_provider import get_fonts
from engine.common.item_selection_view import (
    ItemRow, ItemSelectionTheme, ItemSelectionView,
)

from engine.shop.shop_constants import (
    C_DIM, C_GP, C_HINT, C_MUTED, C_TEXT,
    HEADER_H, MODAL_W,
)
from engine.shop.shop_renderer import (
    draw_dim_overlay, draw_footer, draw_modal_box, draw_shop_header,
)
from engine.common.field_menu_theme import (
    EMBER, GOLD, render_modal, render_panel, wrap_text,
)

# ── Colors (magic-core-shop-specific — field-menu theme) ─────
C_HEADER      = GOLD
C_SEL_BG      = (45, 42, 75)   # unused (row frame is themed)
C_SEL_BDR     = GOLD
C_GP_GAIN     = (132, 196, 111)
C_CONFIRM_TXT = EMBER

# ── Layout (magic-core-shop-specific) ────────────────────────
PAD          = 28
FOOTER_H     = 32
VISIBLE_ROWS = 7


def _theme() -> ItemSelectionTheme:
    return ItemSelectionTheme(
        sel_bg=C_SEL_BG, sel_bdr=C_SEL_BDR,
        cursor=C_HEADER, title_sel=C_TEXT, title_norm=C_MUTED, title_lock=C_DIM,
        subtitle=C_DIM, subtitle_lk=C_DIM,
        right=C_GP, right_lock=C_DIM,
    )


class MagicCoreShopRenderer:
    """Handles all rendering for the magic core shop scene."""

    def __init__(self) -> None:
        self._fonts_ready = False
        self._view = ItemSelectionView(_theme())

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title   = f.get(24, bold=True)
        self._font_row     = f.get(18)
        self._font_gp      = f.get(18)
        self._font_qty     = f.get(22, bold=True)
        self._font_arrow   = f.get(22)
        self._font_hint    = f.get(15)
        self._font_toast   = f.get(22, bold=True)
        self._font_confirm = f.get(17)
        self._fonts_ready = True

    # ── Main entry point ─────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        state: str,
        avail: list[tuple[str, str, int, int]],
        list_sel: int,
        qty: int,
        popup_text: str,
        gp: int,
        selected: tuple[str, str, int, int] | None,
    ) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        draw_dim_overlay(screen)

        mw = MODAL_W
        full_rows = min(len(avail), VISIBLE_ROWS) if avail else 1
        has_overflow = len(avail) > VISIBLE_ROWS
        body_h = self._view.list_height(full_rows, has_overflow) + 12
        mh     = HEADER_H + body_h + FOOTER_H + PAD * 2

        mx = (screen.get_width()  - mw) // 2
        my = (screen.get_height() - mh) // 2

        draw_modal_box(screen, mx, my, mw, mh, C_SEL_BDR, border_width=1)

        draw_shop_header(
            screen, mx, my, mw,
            title_text="Magic Core Exchange",
            title_color=C_HEADER,
            gp=gp,
            gp_color=C_GP,
            font_title=self._font_title,
            font_row=self._font_gp,
            pad=PAD,
        )

        list_y = my + HEADER_H + PAD
        list_h = self._view.list_height(VISIBLE_ROWS, has_overflow)
        list_rect = pygame.Rect(mx, list_y, mw, list_h)

        if not avail:
            empty = self._font_hint.render(
                "No Magic Cores in inventory.", True, C_DIM)
            screen.blit(empty, (mx + PAD, list_y + 16))
        else:
            rows = [self._build_row(item) for item in avail]
            self._view.render(screen, list_rect, rows, list_sel, scroll=0,
                              active=(state == "list"))

        draw_footer(
            screen, mx, my + mh - FOOTER_H - 4, mw, PAD,
            "select · ENTER exchange · ESC close", self._font_hint,
        )

        if state == "qty" and selected:
            self._draw_qty_overlay(screen, mx, my, mw, mh, selected, qty)
        elif state == "confirm" and selected:
            self._draw_confirm_overlay(screen, selected, qty)
        elif state == "popup":
            self._draw_popup(screen, popup_text)

    # ── Row model ────────────────────────────────────────────

    def _build_row(self, item: tuple[str, str, int, int]) -> ItemRow:
        _id, label, rate, qty = item
        return ItemRow(
            title=f"{label}  x {qty}",
            right_text=f"{rate:,} GP",
        )

    # ── Qty overlay ──────────────────────────────────────────

    def _draw_qty_overlay(
        self,
        screen: pygame.Surface,
        mx: int,
        my: int,
        mw: int,
        mh: int,
        sel: tuple[str, str, int, int],
        qty: int,
    ) -> None:
        item_id, label, rate, max_qty = sel
        total = qty * rate

        ow, oh = mw - 40, 140
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        render_panel(screen, pygame.Rect(ox, oy, ow, oh), active=True)

        lbl = self._font_row.render(label, True, C_HEADER)
        screen.blit(lbl, (ox + 20, oy + 14))

        # quantity selector — arrows use non-bold font for glyph compatibility
        left_s  = self._font_arrow.render(" ", True, C_TEXT)
        num_s   = self._font_qty.render(f"  {qty}  ", True, C_TEXT)
        right_s = self._font_arrow.render(" ", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 44
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        max_s = self._font_hint.render(f"max {max_qty}", True, C_DIM)
        screen.blit(max_s, (ox + ow - max_s.get_width() - 16, oy + 52))

        total_s = self._font_gp.render(f"   {total:,} GP", True, C_GP_GAIN)
        screen.blit(total_s, (ox + 20, oy + 95))

        hint = self._font_hint.render(
            "qty ±1    qty ±10    ENTER confirm    ESC back",
            True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, oy + oh - 22))

    # ── Confirm overlay ──────────────────────────────────────

    def _draw_confirm_overlay(
        self,
        screen: pygame.Surface,
        sel: tuple[str, str, int, int],
        qty: int,
    ) -> None:
        _, label, rate, _ = sel
        total = qty * rate

        ow = 480
        inner = ow - 40
        pad_top, hint_gap, pad_bot = 22, 22, 24
        msg = f"Exchange {qty} x {label} for {total:,} GP?"
        lines = wrap_text(self._font_confirm, msg, inner)
        line_h = self._font_confirm.get_height() + 4
        hint = self._font_hint.render(
            "ENTER / Y - Confirm    ESC / N - Cancel", True, C_HINT)

        oh = pad_top + len(lines) * line_h + hint_gap + hint.get_height() + pad_bot
        modal = render_modal(screen, ow, oh)

        y = modal.y + pad_top
        for line in lines:
            screen.blit(
                self._font_confirm.render(line, True, C_CONFIRM_TXT),
                (modal.x + 20, y))
            y += line_h
        screen.blit(hint, (modal.x + 20, y + hint_gap))

    # ── Popup ────────────────────────────────────────────────

    def _draw_popup(self, screen: pygame.Surface, popup_text: str) -> None:
        pw = 460
        lines = wrap_text(self._font_toast, popup_text, pw - 40)
        line_h = self._font_toast.get_height() + 4
        ph = 18 + len(lines) * line_h + 32
        modal = render_modal(screen, pw, ph)
        y = modal.y + 18
        for line in lines:
            msg = self._font_toast.render(line, True, C_GP_GAIN)
            screen.blit(msg, (modal.x + (pw - msg.get_width()) // 2, y))
            y += line_h
        hint = self._font_hint.render("ENTER / ESC  close", True, C_HINT)
        screen.blit(hint, (modal.x + (pw - hint.get_width()) // 2, modal.bottom - 28))
