# engine/shop/item_shop_renderer.py
#
# All rendering for the Item Shop scene.

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ShopViewState:
    """Per-frame snapshot of everything the item shop renderer draws.
    Built by ItemShopScene.render; the renderer holds no scene state."""
    state: str
    mode: str
    avail: list[dict]
    list_sel: int
    scroll: int
    qty: int
    popup_text: str
    gp: int
    sprite_surf: pygame.Surface | None
    selected: dict | None
    owned_qty: Callable[[str], int]
    display_name: Callable[[dict], str]
    row_price: Callable[[dict], int]
    sell_tag: str | None
    description: Callable[[dict], str]
    members: list[MemberState]
    equip_selection: int
    pending_equip_item_id: str | None
    item_catalog: ItemCatalog


@dataclass(frozen=True)
class _ModalLayout:
    """Resolved modal geometry for one frame."""
    mx: int
    my: int
    modal_w: int
    mh: int
    left_w: int
    party_w: int
    list_h: int
    desc_h: int
    body_h: int


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

    def render(self, screen: pygame.Surface, view: ShopViewState) -> None:
        selected_def = self._item_def(view)
        show_party = (
            view.mode == "buy"
            and selected_def is not None
            and selected_def.type in EQUIPMENT_TYPES
        )
        lay = self._layout(screen, view, show_party)

        draw_dim_overlay(screen)
        draw_modal_box(screen, lay.mx, lay.my, lay.modal_w, lay.mh, C_BORDER)
        self._draw_header(screen, view, lay)

        list_rect = pygame.Rect(
            lay.mx + PAD, lay.my + HEADER_H + PAD, lay.left_w, lay.list_h,
        )
        self._draw_list(screen, view, list_rect)

        desc_text = view.description(view.selected) if view.selected else ""
        self._draw_description(
            screen, list_rect.x, list_rect.bottom + DESC_GAP,
            lay.left_w, lay.desc_h, desc_text,
        )

        if show_party and selected_def is not None:
            party_rect = pygame.Rect(
                list_rect.right + COL_GAP, list_rect.y, lay.party_w, lay.body_h,
            )
            self._draw_party_preview(
                screen,
                party_rect,
                view.members,
                selected_def,
                view.item_catalog,
                view.equip_selection,
                active=view.state == "equip",
                pending=view.state == "equip"
                and view.pending_equip_item_id == selected_def.id,
            )

        draw_footer(
            screen, lay.mx, lay.my + lay.mh - FOOTER_H - 4, lay.modal_w, PAD,
            self._footer_hint(view, show_party), self._fonts.hint,
        )

        if view.state == "qty" and view.selected:
            self._draw_qty_overlay(screen, lay, view)
        elif view.state == "popup":
            draw_popup(
                screen, POPUP_W, view.popup_text, C_TOAST, C_BORDER,
                self._fonts.toast, self._fonts.hint,
            )

    # ── Layout ───────────────────────────────────────────────

    def _layout(
        self, screen: pygame.Surface, view: ShopViewState, show_party: bool,
    ) -> _ModalLayout:
        modal_w = min(screen.get_width() - 64, EQUIP_MODAL_W) if show_party else MODAL_W
        left_w = min(MODAL_W - PAD * 2, modal_w - PAD * 2)
        party_w = 0
        if show_party:
            left_w = min(500, max(400, int((modal_w - PAD * 2 - COL_GAP) * 0.52)))
            party_w = modal_w - PAD * 2 - COL_GAP - left_w

        desc_h = self._desc_panel_height()
        full_rows = min(len(view.avail), VISIBLE_ROWS) if view.avail else 1
        has_overflow = len(view.avail) > VISIBLE_ROWS
        list_h = self._view.list_height(full_rows, has_overflow)
        body_h = list_h + DESC_GAP + desc_h
        if show_party:
            body_h = max(body_h, self._party_panel_min_height(view.members))
        mh = HEADER_H + PAD + body_h + FOOTER_H + PAD
        return _ModalLayout(
            mx=(screen.get_width() - modal_w) // 2,
            my=(screen.get_height() - mh) // 2,
            modal_w=modal_w,
            mh=mh,
            left_w=left_w,
            party_w=party_w,
            list_h=list_h,
            desc_h=desc_h,
            body_h=body_h,
        )

    # ── Sections ─────────────────────────────────────────────

    def _draw_header(
        self, screen: pygame.Surface, view: ShopViewState, lay: _ModalLayout,
    ) -> None:
        if view.mode == "buy":
            title_text = f"{self._title} — Buy"
        else:
            tag_label = f"[{view.sell_tag}]" if view.sell_tag else "[All]"
            title_text = f"{self._title} — Sell {tag_label}"
        draw_shop_header(
            screen, lay.mx, lay.my, lay.modal_w,
            title_text=title_text,
            title_color=C_HEADER,
            gp=view.gp,
            gp_color=C_GP,
            font_title=self._fonts.title,
            font_row=self._fonts.row,
            pad=PAD,
            sprite_surf=view.sprite_surf,
            sprite_size=SPRITE_SIZE,
        )

    def _draw_list(
        self, screen: pygame.Surface, view: ShopViewState, list_rect: pygame.Rect,
    ) -> None:
        if not view.avail:
            empty_msg = (
                "No items available." if view.mode == "buy"
                else "Nothing to sell."
            )
            empty = self._fonts.hint.render(empty_msg, True, C_DIM)
            screen.blit(empty, (list_rect.x, list_rect.y + 16))
            return
        rows = [self._build_row(item, view) for item in view.avail]
        self._view.render(
            screen, list_rect, rows, view.list_sel, view.scroll,
            active=(view.state == "list"),
        )

    def _footer_hint(self, view: ShopViewState, show_party: bool) -> str:
        if view.mode != "buy":
            return "TAB buy · T tag · ENTER sell · ESC close"
        if view.state == "equip":
            return "UP/DOWN party · ENTER equip · ESC skip"
        if view.state == "qty":
            return "LEFT/RIGHT qty ±1 · UP/DOWN qty ±5 · ENTER confirm · ESC back"
        if show_party:
            return "UP/DOWN item · LEFT/RIGHT party · ENTER buy · TAB sell · ESC close"
        return "TAB sell · ENTER buy · ESC close"

    def _item_def(self, view: ShopViewState) -> ItemDef | None:
        item_id = view.pending_equip_item_id or (
            view.selected["id"] if view.selected else None
        )
        if not item_id:
            return None
        return view.item_catalog.get(item_id)

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

    def _build_row(self, item: dict, view: ShopViewState) -> ItemRow:
        price = view.row_price(item)
        if view.mode == "buy":
            return ItemRow(
                title=view.display_name(item),
                subtitle=f"owned: {view.owned_qty(item['id'])}",
                right_text=f"{price:,} GP",
                locked=price > view.gp,
            )
        # sell mode: row already carries owned qty
        return ItemRow(
            title=view.display_name(item),
            subtitle=f"owned: {item.get('owned', 0)}",
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
        self, screen: pygame.Surface, lay: _ModalLayout, view: ShopViewState,
    ) -> None:
        sel = view.selected
        price = view.row_price(sel)
        total = view.qty * price

        ow, oh = min(MODAL_W - 40, lay.modal_w - 40), 120
        ox = lay.mx + 20
        oy = lay.my + lay.mh // 2 - oh // 2

        render_panel(screen, pygame.Rect(ox, oy, ow, oh), active=True)

        name = view.display_name(sel)
        lbl  = self._fonts.row.render(name, True, C_HEADER)
        screen.blit(lbl, (ox + 20, oy + 12))

        # qty selector — arrows use non-bold font for glyph compatibility
        left_s  = self._fonts.arrow.render(" ", True, C_TEXT)
        num_s   = self._fonts.qty.render(f"  {view.qty}  ", True, C_TEXT)
        right_s = self._fonts.arrow.render(" ", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 38
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        # total price
        if view.mode == "buy":
            col = C_WARN if total > view.gp else C_GP
            total_s = self._fonts.row.render(f"Total: {total:,} GP", True, col)
            screen.blit(total_s, (ox + 20, oy + 76))
            if total > view.gp:
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
