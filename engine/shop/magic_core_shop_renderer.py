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
    C_BG, C_DIM, C_GP, C_HINT, C_MUTED, C_TEXT,
    HEADER_H, MODAL_W,
)
from engine.shop.shop_renderer import (
    draw_dim_overlay, draw_footer, draw_modal_box, draw_shop_header,
)

# ── Colors (magic-core-shop-specific) ────────────────────────
C_HEADER      = (212, 200, 138)
C_SEL_BG      = (45, 42, 75)
C_SEL_BDR     = (180, 160, 255)
C_GP_GAIN     = (100, 220, 100)
C_CONFIRM_BG  = (28, 14, 14)
C_CONFIRM_BDR = (180, 70, 70)
C_CONFIRM_TXT = (220, 180, 180)

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

        pygame.draw.rect(screen, (22, 22, 44), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR,    (ox, oy, ow, oh), 2, border_radius=6)

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

        ow, oh = 480, 110
        ox = (screen.get_width()  - ow) // 2
        oy = (screen.get_height() - oh) // 2

        pygame.draw.rect(screen, C_CONFIRM_BG,  (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_CONFIRM_BDR, (ox, oy, ow, oh), 2, border_radius=6)

        msg = self._font_confirm.render(
            f"Exchange {qty} x {label} for {total:,} GP?",
            True, C_CONFIRM_TXT)
        screen.blit(msg, (ox + 20, oy + 20))

        hint = self._font_hint.render(
            "ENTER / Y - Confirm    ESC / N - Cancel", True, C_HINT)
        screen.blit(hint, (ox + 20, oy + 64))

    # ── Popup ────────────────────────────────────────────────

    def _draw_popup(self, screen: pygame.Surface, popup_text: str) -> None:
        pw, ph = 460, 80
        px = (screen.get_width()  - pw) // 2
        py = (screen.get_height() - ph) // 2
        pygame.draw.rect(screen, C_BG,      (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR, (px, py, pw, ph), 2, border_radius=6)
        msg = self._font_toast.render(popup_text, True, C_GP_GAIN)
        screen.blit(msg, (px + (pw - msg.get_width()) // 2, py + 14))
        hint = self._font_hint.render("ENTER / ESC  close", True, C_HINT)
        screen.blit(hint, (px + (pw - hint.get_width()) // 2, py + ph - 28))
