# engine/shop/item_shop_renderer.py
#
# All rendering for the Item Shop scene.

from __future__ import annotations

from typing import Callable

import pygame
from engine.common.font_provider import FontSet
from engine.common.item_selection_view import (
    ItemRow, ItemSelectionTheme, ItemSelectionView,
)
from engine.equipment.equipment_logic import can_equip, stat_totals, stat_totals_preview
from engine.item.item_catalog import EQUIPMENT_TYPES, ItemCatalog, ItemDef
from engine.party.member_state import MemberState

from engine.shop.shop_constants import (
    C_DIM, C_GP, C_HINT, C_MUTED, C_TEXT, C_TOAST, C_WARN,
    HEADER_H, MODAL_W,
)
from engine.shop.shop_renderer import (
    draw_dim_overlay, draw_footer, draw_modal_box, draw_popup, draw_shop_header,
)
from engine.common.ui.theme import GOLD
from engine.common.ui.chrome import fit_text, render_panel, render_row_frame, wrap_text

# ── Colors (item-shop-specific — field-menu theme) ──────────
C_BORDER   = GOLD
C_HEADER   = GOLD
C_SEL_BG   = (45, 42, 75)   # unused (row frame is themed)
C_SEL_BDR  = GOLD

# ── Layout (item-shop-specific) ──────────────────────────────
PAD          = 24
SPRITE_SIZE  = 64
FOOTER_H     = 36
VISIBLE_ROWS = 7
POPUP_W      = 360
DESC_PAD     = 12
DESC_LINES   = 2
DESC_GAP     = 10
EQUIP_MODAL_W = 980
COL_GAP = 18
PARTY_TOP = 54
PARTY_BOTTOM_PAD = 14
PARTY_ROW_GAP = 8
PARTY_ROW_MIN_H = 72
PARTY_ROW_MAX_H = 92
STAT_ORDER = ("str", "dex", "con", "int")
STAT_LABEL = {"str": "STR", "dex": "DEX", "con": "CON", "int": "INT"}
SLOT_LABEL = {
    "weapon": "Weapon",
    "shield": "Shield",
    "helmet": "Helmet",
    "body": "Body",
    "accessory": "Accessory",
}
C_UP = (120, 220, 120)
C_DOWN = (220, 110, 110)


def _theme() -> ItemSelectionTheme:
    return ItemSelectionTheme(
        sel_bg=C_SEL_BG, sel_bdr=C_SEL_BDR,
        cursor=C_HEADER, title_sel=C_TEXT, title_norm=C_MUTED, title_lock=C_DIM,
        subtitle=C_DIM, subtitle_lk=C_DIM,
        right=C_GP, right_lock=C_DIM,
    )


class ItemShopRenderer:
    """Handles all rendering for the item shop scene."""

    def __init__(self, title: str) -> None:
        self._title = title
        self._fonts = FontSet(
            title=(22, True), row=16, qty=(20, True), arrow=20,
            hint=15, toast=(20, True), desc=18, party=(15, True), stat=14,
            meta=13,
        )
        self._view = ItemSelectionView(_theme())

    def _desc_panel_height(self) -> int:
        lh = self._fonts.desc.get_height() + 4
        return DESC_PAD * 2 + lh * DESC_LINES

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
        description: Callable[[dict], str] | None = None,
        members: list[MemberState] | None = None,
        equip_selection: int = 0,
        pending_equip_item_id: str | None = None,
        item_catalog: ItemCatalog | None = None,
    ) -> None:

        selected_def = self._item_def(selected, pending_equip_item_id, item_catalog)
        show_party = (
            mode == "buy"
            and selected_def is not None
            and selected_def.type in EQUIPMENT_TYPES
        )
        modal_w = min(screen.get_width() - 64, EQUIP_MODAL_W) if show_party else MODAL_W
        left_w = min(MODAL_W - PAD * 2, modal_w - PAD * 2)
        party_w = 0
        if show_party:
            left_w = min(500, max(400, int((modal_w - PAD * 2 - COL_GAP) * 0.52)))
            party_w = modal_w - PAD * 2 - COL_GAP - left_w

        desc_h = self._desc_panel_height()
        full_rows = min(len(avail), VISIBLE_ROWS) if avail else 1
        has_overflow = len(avail) > VISIBLE_ROWS
        list_h = self._view.list_height(full_rows, has_overflow)
        left_body_h = list_h + DESC_GAP + desc_h
        body_h = left_body_h
        if show_party:
            body_h = max(body_h, self._party_panel_min_height(members or []))
        mh = HEADER_H + PAD + body_h + FOOTER_H + PAD

        mx = (screen.get_width()  - modal_w) // 2
        my = (screen.get_height() - mh) // 2

        draw_dim_overlay(screen)
        draw_modal_box(screen, mx, my, modal_w, mh, C_BORDER)

        if mode == "buy":
            title_text = f"{self._title} — Buy"
        else:
            tag_label = f"[{sell_tag}]" if sell_tag else "[All]"
            title_text = f"{self._title} — Sell {tag_label}"
        draw_shop_header(
            screen, mx, my, modal_w,
            title_text=title_text,
            title_color=C_HEADER,
            gp=gp,
            gp_color=C_GP,
            font_title=self._fonts.title,
            font_row=self._fonts.row,
            pad=PAD,
            sprite_surf=sprite_surf,
            sprite_size=SPRITE_SIZE,
        )

        list_y = my + HEADER_H + PAD
        list_rect = pygame.Rect(mx + PAD, list_y, left_w, list_h)

        if not avail:
            empty_msg = (
                "No items available." if mode == "buy"
                else "Nothing to sell."
            )
            empty = self._fonts.hint.render(empty_msg, True, C_DIM)
            screen.blit(empty, (list_rect.x, list_y + 16))
        else:
            rows = [
                self._build_row(item, gp, owned_qty, display_name, mode, row_price)
                for item in avail
            ]
            self._view.render(screen, list_rect, rows, list_sel, scroll, active=(state == "list"))

        desc_text = description(selected) if (description and selected) else ""
        self._draw_description(
            screen, list_rect.x, list_y + list_h + DESC_GAP,
            left_w, desc_h, desc_text,
        )

        if show_party and selected_def is not None:
            party_rect = pygame.Rect(
                list_rect.right + COL_GAP,
                list_y,
                party_w,
                body_h,
            )
            self._draw_party_preview(
                screen,
                party_rect,
                members or [],
                selected_def,
                item_catalog,
                equip_selection,
                active=state == "equip",
                pending=state == "equip" and pending_equip_item_id == selected_def.id,
            )

        footer_hint = (
            self._footer_hint(mode, state, show_party)
            if mode == "buy"
            else "TAB buy · T tag · ENTER sell · ESC close"
        )
        draw_footer(
            screen, mx, my + mh - FOOTER_H - 4, modal_w, PAD,
            footer_hint, self._fonts.hint,
        )

        if state == "qty" and selected:
            self._draw_qty_overlay(
                screen, mx, my, modal_w, mh, selected, qty, gp, display_name, mode, row_price,
            )
        elif state == "popup":
            draw_popup(
                screen, POPUP_W, popup_text, C_TOAST, C_BORDER,
                self._fonts.toast, self._fonts.hint,
            )

    def _footer_hint(self, mode: str, state: str, show_party: bool) -> str:
        if state == "equip":
            return "UP/DOWN party · ENTER equip · ESC skip"
        if state == "qty":
            return "LEFT/RIGHT qty ±1 · UP/DOWN qty ±5 · ENTER confirm · ESC back"
        if mode == "buy" and show_party:
            return "UP/DOWN item · LEFT/RIGHT party · ENTER buy · TAB sell · ESC close"
        return "TAB sell · ENTER buy · ESC close"

    def _item_def(
        self,
        selected: dict | None,
        pending_equip_item_id: str | None,
        item_catalog: ItemCatalog | None,
    ) -> ItemDef | None:
        if item_catalog is None:
            return None
        item_id = pending_equip_item_id or (selected["id"] if selected else None)
        if not item_id:
            return None
        return item_catalog.get(item_id)

    def _party_panel_min_height(self, members: list[MemberState]) -> int:
        if not members:
            return PARTY_TOP + PARTY_BOTTOM_PAD + PARTY_ROW_MIN_H
        return (
            PARTY_TOP
            + PARTY_BOTTOM_PAD
            + len(members) * PARTY_ROW_MIN_H
            + max(0, len(members) - 1) * PARTY_ROW_GAP
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

    # ── Description band ─────────────────────────────────────

    def _draw_description(
        self, screen: pygame.Surface, x: int, y: int,
        panel_w: int, panel_h: int, text: str,
    ) -> None:
        render_panel(screen, pygame.Rect(x, y, panel_w, panel_h))

        if not text:
            text = "—"
        font = self._fonts.desc
        lh = font.get_height() + 4
        inner_w = panel_w - DESC_PAD * 2
        lines = wrap_text(font, text, inner_w, limit=DESC_LINES)
        tx, ty = x + DESC_PAD, y + DESC_PAD
        for i, ln in enumerate(lines):
            screen.blit(font.render(ln, True, C_TEXT), (tx, ty + i * lh))

    # ── Qty overlay ──────────────────────────────────────────

    def _draw_qty_overlay(
        self,
        screen: pygame.Surface,
        mx: int,
        my: int,
        modal_w: int,
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

        ow, oh = min(MODAL_W - 40, modal_w - 40), 120
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        render_panel(screen, pygame.Rect(ox, oy, ow, oh), active=True)

        name = display_name(sel)
        lbl  = self._fonts.row.render(name, True, C_HEADER)
        screen.blit(lbl, (ox + 20, oy + 12))

        # qty selector — arrows use non-bold font for glyph compatibility
        left_s  = self._fonts.arrow.render(" ", True, C_TEXT)
        num_s   = self._fonts.qty.render(f"  {qty}  ", True, C_TEXT)
        right_s = self._fonts.arrow.render(" ", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 38
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        # total price
        if mode == "buy":
            col = C_WARN if total > gp else C_GP
            total_s = self._fonts.row.render(f"Total: {total:,} GP", True, col)
            screen.blit(total_s, (ox + 20, oy + 76))
            if total > gp:
                warn = self._fonts.hint.render("Not enough GP", True, C_WARN)
                screen.blit(warn, (ox + ow - warn.get_width() - 20, oy + 80))
        else:
            total_s = self._fonts.row.render(f"Receive: {total:,} GP", True, C_GP)
            screen.blit(total_s, (ox + 20, oy + 76))

        hint = self._fonts.hint.render(
            "qty ±1    qty ±5    ENTER confirm    ESC back",
            True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, oy + oh - 20))

    # ── Equipment party preview ──────────────────────────────

    def _draw_party_preview(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        members: list[MemberState],
        item: ItemDef,
        catalog: ItemCatalog,
        selection: int,
        *,
        active: bool,
        pending: bool,
    ) -> None:
        render_panel(screen, rect, active=active, title="Party", title_font=self._fonts.party)
        title = f"{SLOT_LABEL.get(item.type, item.type.title())}: {item.name}"
        title_s = self._fonts.meta.render(title, True, C_GP)
        screen.blit(title_s, (rect.x + 14, rect.y + 28))

        if not members:
            msg = self._fonts.row.render("No party members.", True, C_DIM)
            screen.blit(msg, (rect.x + 14, rect.y + 56))
            return

        top = rect.y + PARTY_TOP
        gap = PARTY_ROW_GAP
        available_h = rect.bottom - PARTY_BOTTOM_PAD - top - gap * (len(members) - 1)
        row_h = min(PARTY_ROW_MAX_H, max(PARTY_ROW_MIN_H, available_h // len(members)))
        for idx, member in enumerate(members):
            row = pygame.Rect(rect.x + 12, top + idx * (row_h + gap), rect.w - 24, row_h)
            focused = active and idx == selection
            dimmed = (not active) and idx == selection
            self._draw_member_preview_row(screen, row, member, item, catalog, focused, dimmed, pending)

    def _draw_member_preview_row(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        member: MemberState,
        item: ItemDef,
        catalog: ItemCatalog,
        focused: bool,
        dimmed: bool,
        pending: bool,
    ) -> None:
        allowed = can_equip(member, item)
        render_row_frame(screen, rect, focused=focused, dimmed_sel=dimmed)
        name_color = C_TEXT if allowed else C_DIM
        name = self._fonts.party.render(f"{member.name}  Lv{member.level}", True, name_color)
        screen.blit(name, (rect.x + 10, rect.y + 8))
        current_item = self._equipped_label(member, item.type, catalog) if allowed else "Cannot equip"
        equip_line = fit_text(
            self._fonts.meta,
            current_item,
            C_MUTED if allowed else C_WARN,
            rect.w // 2,
        )
        screen.blit(equip_line, (rect.right - equip_line.get_width() - 10, rect.y + 10))

        current = stat_totals(member, catalog)
        after = stat_totals_preview(member, catalog, item.type, item.id)
        stat_y = rect.y + 38
        stat_w = max(62, (rect.w - 20) // len(STAT_ORDER))
        for i, key in enumerate(STAT_ORDER):
            before = current.get(key, 0)
            now = after.get(key, 0) if allowed else before
            color = C_TEXT
            if allowed and now > before:
                color = C_UP
            elif allowed and now < before:
                color = C_DOWN
            text = f"{STAT_LABEL[key]} {before}->{now}"
            stat = self._fonts.stat.render(text, True, color if allowed else C_DIM)
            screen.blit(stat, (rect.x + 10 + i * stat_w, stat_y))

        if pending and focused and allowed:
            hint = self._fonts.meta.render("ENTER equips", True, C_GP)
            screen.blit(hint, (rect.right - hint.get_width() - 10, rect.bottom - 18))

    def _equipped_label(self, member: MemberState, slot: str, catalog: ItemCatalog) -> str:
        item_id = member.equipped.get(slot) or ""
        if not item_id:
            return "Now: -"
        defn = catalog.get(item_id)
        name = defn.name if defn else item_id.replace("_", " ").title()
        return f"Now: {name}"
