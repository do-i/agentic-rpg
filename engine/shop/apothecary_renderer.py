# engine/shop/apothecary_renderer.py
#
# All rendering for the Apothecary scene.

from __future__ import annotations

from typing import Callable

import pygame
from engine.common.font_provider import get_fonts
from engine.common.item_selection_view import (
    ItemRow, ItemSelectionTheme, ItemSelectionView,
)

from engine.shop.shop_constants import (
    C_DIM, C_DIVIDER, C_GP, C_HINT, C_LOCKED, C_MUTED, C_TEXT, C_TOAST,
    C_WARN, HEADER_H, MODAL_W,
)
from engine.shop.shop_renderer import (
    draw_dim_overlay, draw_footer, draw_modal_box, draw_popup, draw_shop_header,
)

# ── Colors (apothecary-specific) ─────────────────────────────
C_BORDER  = (120, 160, 120)
C_HEADER  = (180, 220, 180)
C_SEL_BG  = (35, 50, 42)
C_SEL_BDR = (130, 200, 140)
C_READY   = (100, 200, 120)
C_MISSING = (200, 130, 100)

# ── Layout (apothecary-specific) ─────────────────────────────
PAD          = 24
SPRITE_SIZE  = 64
FOOTER_H     = 36
VISIBLE_ROWS = 7
POPUP_W      = 360


def _theme() -> ItemSelectionTheme:
    return ItemSelectionTheme(
        sel_bg=C_SEL_BG, sel_bdr=C_SEL_BDR,
        cursor=C_HEADER, title_sel=C_TEXT, title_norm=C_MUTED, title_lock=C_LOCKED,
        subtitle=C_DIM, subtitle_lk=C_LOCKED,
        right=C_GP, right_lock=C_DIM,
    )


class ApothecaryRenderer:
    """Handles all rendering for the apothecary scene."""

    def __init__(self) -> None:
        self._fonts_ready = False
        self._view = ItemSelectionView(_theme())

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title    = f.get(22, bold=True)
        self._font_row      = f.get(16)
        self._font_detail    = f.get(16)
        self._font_detail_b  = f.get(16, bold=True)
        self._font_hint      = f.get(15)
        self._font_toast     = f.get(20, bold=True)
        self._fonts_ready = True

    # ── Main entry point ─────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        state: str,
        recipes: list[dict],
        list_sel: int,
        scroll: int,
        popup_text: str,
        gp: int,
        sprite_surf: pygame.Surface | None,
        is_unlocked: Callable[[dict], bool],
        has_inputs: Callable[[dict], bool],
        can_afford: Callable[[dict], bool],
        can_craft: Callable[[dict], bool],
        item_name: Callable[[str], str],
        mc_name: Callable[[str], str],
        owned_qty: Callable[[str], int],
        selected: dict | None,
        icons: dict[str, pygame.Surface] | None = None,
    ) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        full_rows = min(len(recipes), VISIBLE_ROWS) if recipes else 1
        has_overflow = len(recipes) > VISIBLE_ROWS
        body_h = self._view.list_height(full_rows, has_overflow) + 12
        mh     = HEADER_H + body_h + FOOTER_H + PAD * 2

        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - mh) // 2

        draw_dim_overlay(screen)
        draw_modal_box(screen, mx, my, MODAL_W, mh, C_BORDER)

        draw_shop_header(
            screen, mx, my, MODAL_W,
            title_text="Apothecary",
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

        if not recipes:
            empty = self._font_hint.render("No recipes available.", True, C_DIM)
            screen.blit(empty, (mx + PAD, list_y + 16))
        else:
            rows = [
                self._build_row(r, is_unlocked, has_inputs, can_afford, item_name, icons or {})
                for r in recipes
            ]
            self._view.render(screen, list_rect, rows, list_sel, scroll, active=(state == "list"))

        draw_footer(
            screen, mx, my + mh - FOOTER_H - 4, MODAL_W, PAD,
            "select · ENTER view · ESC close", self._font_hint,
        )

        if state == "detail" and selected:
            self._draw_detail_overlay(
                screen, mx, my, mh, selected, gp, is_unlocked, can_afford,
                can_craft, item_name, mc_name, owned_qty,
            )
        elif state == "popup":
            draw_popup(
                screen, POPUP_W, popup_text, C_TOAST, C_BORDER,
                self._font_toast, self._font_hint,
            )

    # ── Row model ────────────────────────────────────────────

    def _build_row(
        self,
        recipe: dict,
        is_unlocked: Callable[[dict], bool],
        has_inputs: Callable[[dict], bool],
        can_afford: Callable[[dict], bool],
        item_name: Callable[[str], str],
        icons: dict[str, pygame.Surface],
    ) -> ItemRow:
        unlocked = is_unlocked(recipe)
        ready    = unlocked and has_inputs(recipe) and can_afford(recipe)

        if not unlocked:
            icon_key = "locked"
        elif ready:
            icon_key = "ready"
        else:
            icon_key = "missing"
        icon_surf = icons.get(icon_key)

        scroll_name = recipe.get("scroll_name", recipe["id"])

        if unlocked:
            output = recipe.get("output", {})
            out_id = output.get("item", "")
            out_qty = output.get("qty", 1)
            subtitle = f"{item_name(out_id)} x{out_qty}"
            right_text = f"{recipe.get('gp_cost', 0):,} GP"
        else:
            subtitle = "-----"
            right_text = None

        return ItemRow(
            title=scroll_name,
            subtitle=subtitle,
            icon=icon_surf,
            right_text=right_text,
            locked=not unlocked,
        )

    # ── Detail overlay ───────────────────────────────────────

    _MC_SIZE_TO_ID = {"XS": "mc_xs", "S": "mc_s", "M": "mc_m", "L": "mc_l", "XL": "mc_xl"}

    def _draw_detail_overlay(
        self,
        screen: pygame.Surface,
        mx: int,
        my: int,
        mh: int,
        sel: dict,
        gp: int,
        is_unlocked: Callable[[dict], bool],
        can_afford: Callable[[dict], bool],
        can_craft: Callable[[dict], bool],
        item_name: Callable[[str], str],
        mc_name: Callable[[str], str],
        owned_qty: Callable[[str], int],
    ) -> None:
        inputs = sel.get("inputs", {})
        item_inputs = inputs.get("items", [])
        mc_inputs = inputs.get("mc", [])
        input_count = len(item_inputs) + len(mc_inputs)
        gp_cost = sel.get("gp_cost", 0)
        output = sel.get("output", {})
        out_id = output.get("item", "")
        out_qty = output.get("qty", 1)
        out_name = item_name(out_id)

        # overlay height: output + inputs + cost + hints
        line_h = 22
        oh = 60 + input_count * line_h + 70
        ow = MODAL_W - 40
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        pygame.draw.rect(screen, (22, 22, 44), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR,    (ox, oy, ow, oh), 2, border_radius=6)

        cy = oy + 14

        # recipe name
        scroll_name = sel.get("scroll_name", sel["id"])
        lbl = self._font_detail_b.render(scroll_name, True, C_HEADER)
        screen.blit(lbl, (ox + 20, cy))
        cy += 28

        # output
        out_s = self._font_detail.render(f"Output:  {out_name} x{out_qty}", True, C_READY)
        screen.blit(out_s, (ox + 20, cy))
        cy += 24

        # divider
        pygame.draw.line(screen, C_DIVIDER, (ox + 20, cy), (ox + ow - 20, cy))
        cy += 8

        # inputs header
        inp_lbl = self._font_detail_b.render("Inputs:", True, C_TEXT)
        screen.blit(inp_lbl, (ox + 20, cy))
        cy += line_h

        # item inputs
        for req in item_inputs:
            item_id = req["id"]
            req_qty = req["qty"]
            owned = owned_qty(item_id)
            name = item_name(item_id)
            has_enough = owned >= req_qty
            color = C_TEXT if has_enough else C_WARN
            txt = f"  {name}  x{req_qty}  (owned: {owned})"
            s = self._font_detail.render(txt, True, color)
            screen.blit(s, (ox + 28, cy))
            cy += line_h

        # MC inputs
        for req in mc_inputs:
            size = req["size"]
            req_qty = req["qty"]
            mc_id = self._MC_SIZE_TO_ID.get(size, "")
            owned = owned_qty(mc_id)
            name = mc_name(size)
            has_enough = owned >= req_qty
            color = C_TEXT if has_enough else C_WARN
            txt = f"  {name}  x{req_qty}  (owned: {owned})"
            s = self._font_detail.render(txt, True, color)
            screen.blit(s, (ox + 28, cy))
            cy += line_h

        cy += 4

        # GP cost
        affordable = can_afford(sel)
        gp_color = C_GP if affordable else C_WARN
        gp_s = self._font_detail.render(
            f"Cost: {gp_cost:,} GP", True, gp_color)
        screen.blit(gp_s, (ox + 20, cy))

        bal_s = self._font_detail.render(f"Balance: {gp:,} GP", True, C_DIM)
        screen.blit(bal_s, (ox + ow - bal_s.get_width() - 20, cy))
        cy += 28

        # hint line
        can = can_craft(sel)
        if can:
            hint_text = "ENTER craft · ESC back"
        else:
            hint_text = "ESC back"
        hint = self._font_hint.render(hint_text, True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, cy))
