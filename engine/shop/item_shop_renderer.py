# engine/shop/item_shop_renderer.py
#
# All rendering for the Item Shop scene.

from __future__ import annotations

from typing import Callable

import pygame

from engine.shop.shop_constants import (
    C_DIM, C_GP, C_HINT, C_MUTED, C_TEXT, C_TOAST, C_WARN,
    HEADER_H, MODAL_W, ROW_GAP,
)
from engine.shop.shop_renderer import (
    draw_cursor_arrow, draw_dim_overlay, draw_footer, draw_list_row_box,
    draw_modal_box, draw_popup, draw_scroll_hints, draw_shop_header,
)

# ── Colors (item-shop-specific) ──────────────────────────────
C_BORDER  = (160, 160, 100)
C_HEADER  = (220, 220, 180)
C_SEL_BG  = (45, 42, 75)
C_SEL_BDR = (180, 160, 255)

# ── Layout (item-shop-specific) ──────────────────────────────
PAD          = 24
SPRITE_SIZE  = 64
ROW_H        = 44
FOOTER_H     = 36
VISIBLE_ROWS = 6
POPUP_W      = 360


class ItemShopRenderer:
    """Handles all rendering for the item shop scene."""

    def __init__(self) -> None:
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_row    = pygame.font.SysFont("Arial", 16)
        self._font_qty    = pygame.font.SysFont("Arial", 20, bold=True)
        self._font_arrow  = pygame.font.SysFont("Arial", 20)
        self._font_hint   = pygame.font.SysFont("Arial", 15)
        self._font_toast  = pygame.font.SysFont("Arial", 20, bold=True)
        self._fonts_ready = True

    # ── Main entry point ─────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        state: str,
        avail: list[dict],
        list_sel: int,
        scroll: int,
        qty: int,
        popup_text: str,
        gp: int,
        sprite_surf: pygame.Surface | None,
        selected: dict | None,
        owned_qty: Callable[[str], int],
        display_name: Callable[[dict], str],
    ) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        rows   = min(len(avail), VISIBLE_ROWS) if avail else 1
        body_h = rows * (ROW_H + ROW_GAP) + 12
        mh     = HEADER_H + body_h + FOOTER_H + PAD * 2

        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - mh) // 2

        draw_dim_overlay(screen)
        draw_modal_box(screen, mx, my, MODAL_W, mh, C_BORDER)

        draw_shop_header(
            screen, mx, my, MODAL_W,
            title_text="Item Shop",
            title_color=C_HEADER,
            gp=gp,
            gp_color=C_GP,
            font_title=self._font_title,
            font_row=self._font_row,
            pad=PAD,
            sprite_surf=sprite_surf,
            sprite_size=SPRITE_SIZE,
        )
        self._draw_list(
            screen, mx, my + HEADER_H + PAD, state, avail, list_sel,
            scroll, gp, owned_qty, display_name,
        )
        draw_footer(
            screen, mx, my + mh - FOOTER_H - 4, MODAL_W, PAD,
            "↑↓ select · ENTER buy · ESC close", self._font_hint,
        )

        if state == "qty" and selected:
            self._draw_qty_overlay(
                screen, mx, my, mh, selected, qty, gp, display_name,
            )
        elif state == "popup":
            draw_popup(
                screen, POPUP_W, popup_text, C_TOAST, C_BORDER,
                self._font_toast, self._font_hint,
            )

    # ── List ─────────────────────────────────────────────────

    def _draw_list(
        self,
        screen: pygame.Surface,
        mx: int,
        y: int,
        state: str,
        avail: list[dict],
        list_sel: int,
        scroll: int,
        gp: int,
        owned_qty: Callable[[str], int],
        display_name: Callable[[dict], str],
    ) -> None:
        if not avail:
            empty = self._font_hint.render("No items available.", True, C_DIM)
            screen.blit(empty, (mx + PAD, y + 16))
            return

        for i in range(VISIBLE_ROWS):
            idx = scroll + i
            if idx >= len(avail):
                break
            item       = avail[idx]
            sel        = (idx == list_sel) and state == "list"
            price      = item.get("buy_price", 0)
            affordable = price <= gp
            row_y      = y + i * (ROW_H + ROW_GAP)
            rx         = mx + 10
            rw         = MODAL_W - 20

            draw_list_row_box(screen, rx, row_y, rw, ROW_H, sel, C_SEL_BG, C_SEL_BDR)

            if sel:
                draw_cursor_arrow(screen, rx, row_y, ROW_H, C_HEADER, self._font_row)

            name   = display_name(item)
            name_c = C_DIM if not affordable else (C_TEXT if sel else C_MUTED)
            lbl    = self._font_row.render(name, True, name_c)
            screen.blit(lbl, (rx + 28, row_y + 6))

            owned = owned_qty(item["id"])
            own_s = self._font_hint.render(f"owned: {owned}", True, C_DIM)
            screen.blit(own_s, (rx + 28, row_y + ROW_H - own_s.get_height() - 4))

            price_c = C_DIM if not affordable else C_GP
            price_s = self._font_row.render(f"{price:,} GP", True, price_c)
            screen.blit(price_s, (rx + rw - price_s.get_width() - 16,
                                   row_y + (ROW_H - price_s.get_height()) // 2))

        draw_scroll_hints(
            screen, mx, y, MODAL_W,
            scroll, len(avail), VISIBLE_ROWS, ROW_H, ROW_GAP,
            self._font_hint,
        )

    # ── Qty overlay ──────────────────────────────────────────

    def _draw_qty_overlay(
        self,
        screen: pygame.Surface,
        mx: int,
        my: int,
        mh: int,
        sel: dict,
        qty: int,
        gp: int,
        display_name: Callable[[dict], str],
    ) -> None:
        price = sel.get("buy_price", 0)
        total = qty * price

        ow, oh = MODAL_W - 40, 120
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        pygame.draw.rect(screen, (22, 22, 44), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR,    (ox, oy, ow, oh), 2, border_radius=6)

        name = display_name(sel)
        lbl  = self._font_row.render(name, True, C_HEADER)
        screen.blit(lbl, (ox + 20, oy + 12))

        # qty selector — arrows use non-bold font for glyph compatibility
        left_s  = self._font_arrow.render("◀", True, C_TEXT)
        num_s   = self._font_qty.render(f"  {qty}  ", True, C_TEXT)
        right_s = self._font_arrow.render("▶", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 38
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        # total price
        col = C_WARN if total > gp else C_GP
        total_s = self._font_row.render(f"Total: {total:,} GP", True, col)
        screen.blit(total_s, (ox + 20, oy + 76))

        if total > gp:
            warn = self._font_hint.render("Not enough GP", True, C_WARN)
            screen.blit(warn, (ox + ow - warn.get_width() - 20, oy + 80))

        hint = self._font_hint.render(
            "← → qty ±1    ↑ ↓ qty ±5    ENTER confirm    ESC back",
            True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, oy + oh - 20))
