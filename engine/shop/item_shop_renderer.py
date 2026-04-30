# engine/shop/item_shop_renderer.py
#
# All rendering for the Item Shop scene.

from __future__ import annotations

from typing import Callable

import pygame
from engine.common.font_provider import get_fonts
from engine.common.item_selection_view import (
    ItemRow, ItemSelectionTheme, ItemSelectionView,
)

from engine.shop.shop_constants import (
    C_DIM, C_GP, C_HINT, C_MUTED, C_TEXT, C_TOAST, C_WARN,
    HEADER_H, MODAL_W,
)
from engine.shop.shop_renderer import (
    draw_dim_overlay, draw_footer, draw_modal_box, draw_popup, draw_shop_header,
)

# ── Colors (item-shop-specific) ──────────────────────────────
C_BORDER  = (160, 160, 100)
C_HEADER  = (220, 220, 180)
C_SEL_BG  = (45, 42, 75)
C_SEL_BDR = (180, 160, 255)

# ── Layout (item-shop-specific) ──────────────────────────────
PAD          = 24
SPRITE_SIZE  = 64
FOOTER_H     = 36
VISIBLE_ROWS = 7
POPUP_W      = 360


def _theme() -> ItemSelectionTheme:
    return ItemSelectionTheme(
        sel_bg=C_SEL_BG, sel_bdr=C_SEL_BDR,
        cursor=C_HEADER, title_sel=C_TEXT, title_norm=C_MUTED, title_lock=C_DIM,
        subtitle=C_DIM, subtitle_lk=C_DIM,
        right=C_GP, right_lock=C_DIM,
    )


class ItemShopRenderer:
    """Handles all rendering for the item shop scene."""

    def __init__(self) -> None:
        self._fonts_ready = False
        self._view = ItemSelectionView(_theme())

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title  = f.get(22, bold=True)
        self._font_row    = f.get(16)
        self._font_qty    = f.get(20, bold=True)
        self._font_arrow  = f.get(20)
        self._font_hint   = f.get(15)
        self._font_toast  = f.get(20, bold=True)
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
        *,
        mode: str = "buy",
        row_price: Callable[[dict], int] | None = None,
        sell_tag: str | None = None,
    ) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        full_rows = min(len(avail), VISIBLE_ROWS) if avail else 1
        has_overflow = len(avail) > VISIBLE_ROWS
        body_h = self._view.list_height(full_rows, has_overflow) + 12
        mh     = HEADER_H + body_h + FOOTER_H + PAD * 2

        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - mh) // 2

        draw_dim_overlay(screen)
        draw_modal_box(screen, mx, my, MODAL_W, mh, C_BORDER)

        if mode == "buy":
            title_text = "Item Shop — Buy"
        else:
            tag_label = f"[{sell_tag}]" if sell_tag else "[All]"
            title_text = f"Item Shop — Sell {tag_label}"
        draw_shop_header(
            screen, mx, my, MODAL_W,
            title_text=title_text,
            title_color=C_HEADER,
            gp=gp,
            gp_color=C_GP,
            font_title=self._font_title,
            font_row=self._font_row,
            pad=PAD,
            sprite_surf=sprite_surf,
            sprite_size=SPRITE_SIZE,
        )

        list_y = my + HEADER_H + PAD
        list_h = self._view.list_height(VISIBLE_ROWS, has_overflow)
        list_rect = pygame.Rect(mx, list_y, MODAL_W, list_h)

        if not avail:
            empty_msg = (
                "No items available." if mode == "buy"
                else "Nothing to sell."
            )
            empty = self._font_hint.render(empty_msg, True, C_DIM)
            screen.blit(empty, (mx + PAD, list_y + 16))
        else:
            rows = [
                self._build_row(item, gp, owned_qty, display_name, mode, row_price)
                for item in avail
            ]
            self._view.render(screen, list_rect, rows, list_sel, scroll, active=(state == "list"))

        footer_hint = (
            "TAB sell · ENTER buy · ESC close" if mode == "buy"
            else "TAB buy · T tag · ENTER sell · ESC close"
        )
        draw_footer(
            screen, mx, my + mh - FOOTER_H - 4, MODAL_W, PAD,
            footer_hint, self._font_hint,
        )

        if state == "qty" and selected:
            self._draw_qty_overlay(
                screen, mx, my, mh, selected, qty, gp, display_name, mode, row_price,
            )
        elif state == "popup":
            draw_popup(
                screen, POPUP_W, popup_text, C_TOAST, C_BORDER,
                self._font_toast, self._font_hint,
            )

    # ── Row model ────────────────────────────────────────────

    def _build_row(
        self,
        item: dict,
        gp: int,
        owned_qty: Callable[[str], int],
        display_name: Callable[[dict], str],
        mode: str,
        row_price: Callable[[dict], int] | None,
    ) -> ItemRow:
        price = row_price(item) if row_price else item["buy_price"]
        if mode == "buy":
            affordable = price <= gp
            owned = owned_qty(item["id"])
            return ItemRow(
                title=display_name(item),
                subtitle=f"owned: {owned}",
                right_text=f"{price:,} GP",
                locked=not affordable,
            )
        # sell mode: row already carries owned qty
        owned = item.get("owned", 0)
        return ItemRow(
            title=display_name(item),
            subtitle=f"owned: {owned}",
            right_text=f"{price:,} GP",
            locked=False,
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
        mode: str,
        row_price: Callable[[dict], int] | None,
    ) -> None:
        price = row_price(sel) if row_price else sel["buy_price"]
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
        left_s  = self._font_arrow.render(" ", True, C_TEXT)
        num_s   = self._font_qty.render(f"  {qty}  ", True, C_TEXT)
        right_s = self._font_arrow.render(" ", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 38
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        # total price
        if mode == "buy":
            col = C_WARN if total > gp else C_GP
            total_s = self._font_row.render(f"Total: {total:,} GP", True, col)
            screen.blit(total_s, (ox + 20, oy + 76))
            if total > gp:
                warn = self._font_hint.render("Not enough GP", True, C_WARN)
                screen.blit(warn, (ox + ow - warn.get_width() - 20, oy + 80))
        else:
            total_s = self._font_row.render(f"Receive: {total:,} GP", True, C_GP)
            screen.blit(total_s, (ox + 20, oy + 76))

        hint = self._font_hint.render(
            "qty ±1    qty ±5    ENTER confirm    ESC back",
            True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, oy + oh - 20))
