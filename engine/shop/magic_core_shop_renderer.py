# engine/shop/magic_core_shop_renderer.py
#
# All rendering for the Magic Core Shop scene.

from __future__ import annotations

import pygame

from engine.shop.shop_constants import (
    C_BG, C_DIM, C_GP, C_HINT, C_MUTED, C_TEXT,
    HEADER_H, MODAL_W, ROW_GAP,
)
from engine.shop.shop_renderer import (
    draw_cursor_arrow, draw_dim_overlay, draw_footer, draw_list_row_box,
    draw_modal_box, draw_shop_header,
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
PAD      = 28
ROW_H    = 52
FOOTER_H = 32


class MagicCoreShopRenderer:
    """Handles all rendering for the magic core shop scene."""

    def __init__(self) -> None:
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        self._font_title   = pygame.font.SysFont("Arial", 24, bold=True)
        self._font_row     = pygame.font.SysFont("Arial", 18)
        self._font_gp      = pygame.font.SysFont("Arial", 18)
        self._font_qty     = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_arrow   = pygame.font.SysFont("Arial", 22)
        self._font_hint    = pygame.font.SysFont("Arial", 15)
        self._font_toast   = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_confirm = pygame.font.SysFont("Arial", 17)
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

        mw     = MODAL_W
        rows   = max(len(avail), 1)
        body_h = rows * (ROW_H + ROW_GAP) + 12
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
        self._draw_list(screen, mx, my + HEADER_H + PAD, mw, state, avail, list_sel)
        draw_footer(
            screen, mx, my + mh - FOOTER_H - 4, mw, PAD,
            "↑↓ select · ENTER exchange · ESC close", self._font_hint,
        )

        if state == "qty" and selected:
            self._draw_qty_overlay(screen, mx, my, mw, mh, selected, qty)
        elif state == "confirm" and selected:
            self._draw_confirm_overlay(screen, selected, qty)
        elif state == "popup":
            self._draw_popup(screen, popup_text)

    # ── List ─────────────────────────────────────────────────

    def _draw_list(
        self,
        screen: pygame.Surface,
        mx: int,
        y: int,
        mw: int,
        state: str,
        avail: list[tuple[str, str, int, int]],
        list_sel: int,
    ) -> None:
        if not avail:
            empty = self._font_hint.render(
                "No Magic Cores in inventory.", True, C_DIM)
            screen.blit(empty, (mx + PAD, y + 16))
            return

        for i, (item_id, label, rate, qty) in enumerate(avail):
            sel   = (i == list_sel) and state == "list"
            row_y = y + i * (ROW_H + ROW_GAP)
            rx    = mx + 10
            rw    = mw - 20

            draw_list_row_box(screen, rx, row_y, rw, ROW_H, sel, C_SEL_BG, C_SEL_BDR)

            if sel:
                draw_cursor_arrow(screen, rx, row_y, ROW_H, C_HEADER, self._font_row)

            # label + qty
            lbl = self._font_row.render(label, True, C_TEXT if sel else C_MUTED)
            screen.blit(lbl, (rx + 28, row_y + 8))

            qty_s = self._font_row.render(f"×  {qty}", True, C_HEADER)
            screen.blit(qty_s, (rx + 28, row_y + ROW_H - qty_s.get_height() - 8))

            # rate + total
            rate_s = self._font_row.render(
                f"{rate:,} GP each    →    {qty * rate:,} GP total",
                True, C_GP_GAIN if sel else C_GP)
            screen.blit(rate_s, (rx + rw - rate_s.get_width() - 16,
                                  row_y + (ROW_H - rate_s.get_height()) // 2))

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
        left_s  = self._font_arrow.render("◀", True, C_TEXT)
        num_s   = self._font_qty.render(f"  {qty}  ", True, C_TEXT)
        right_s = self._font_arrow.render("▶", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 44
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        max_s = self._font_hint.render(f"max {max_qty}", True, C_DIM)
        screen.blit(max_s, (ox + ow - max_s.get_width() - 16, oy + 52))

        total_s = self._font_gp.render(f"→  {total:,} GP", True, C_GP_GAIN)
        screen.blit(total_s, (ox + 20, oy + 95))

        hint = self._font_hint.render(
            "← / → qty ±1    ↑ / ↓ qty ±10    ENTER confirm    ESC back",
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
            f"Exchange {qty} × {label} for {total:,} GP?",
            True, C_CONFIRM_TXT)
        screen.blit(msg, (ox + 20, oy + 20))

        hint = self._font_hint.render(
            "ENTER / Y — Confirm    ESC / N — Cancel", True, C_HINT)
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
