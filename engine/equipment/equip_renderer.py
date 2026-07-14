# engine/equipment/equip_renderer.py
#
# All rendering for the field equip scene: three-panel layout (party /
# slots / picker), stat totals, before-after preview, and key hints.
# The renderer holds no scene state; EquipScene builds an EquipViewState
# per frame and passes it in.

from __future__ import annotations

from dataclasses import dataclass

import pygame

from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.color_constants import (
    C_TEXT_MUT, C_TEXT_DIM, C_HEAD,
)
from engine.common.ui.theme import DIM, GOLD, INK, MUTED
from engine.common.ui.chrome import (
    draw_divider,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    wrap_text,
)
from engine.common.member_card import member_column_width, render_member_column
from engine.item.item_catalog import ItemCatalog, ItemDef
from engine.party.member_state import MemberState
from engine.equipment.equipment_logic import stat_totals, stat_totals_preview


PAGE_MEMBER = "member"
PAGE_SLOT   = "slot"
PAGE_PICKER = "picker"

SLOTS: tuple[str, ...] = ("weapon", "shield", "helmet", "body", "accessory")
SLOT_LABEL = {
    "weapon":    "Weapon",
    "shield":    "Shield",
    "helmet":    "Helmet",
    "body":      "Body",
    "accessory": "Accessory",
}

STAT_ORDER = ("str", "dex", "con", "int")
STAT_LABEL = {"str": "STR", "dex": "DEX", "con": "CON", "int": "INT"}

C_UP   = (120, 220, 120)
C_DOWN = (220, 110, 110)

PAD_X = 40
PAD_Y = 30
GAP = 18
COL_W = 285
ROW_H = 54


@dataclass
class PickerRow:
    item_id: str | None      # None = Unequip row
    item: ItemDef | None     # None for Unequip row


@dataclass(frozen=True)
class EquipViewState:
    """Per-frame snapshot of everything the equip renderer draws.
    Built by EquipScene.render; the renderer holds no scene state."""
    page_id: str
    members: list[MemberState]
    member: MemberState | None
    slot: str
    member_selection: int
    slot_selection: int
    picker_selection: int
    picker_rows: list[PickerRow]


class EquipRenderer:
    def __init__(self, catalog: ItemCatalog) -> None:
        self._catalog = catalog
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_stat  = f.get(16)
        self._font_hint  = f.get(14)
        self._font_meta  = f.get(CAPTION)
        self._fonts_ready = True

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, view: EquipViewState) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        render_backdrop(screen)
        render_header(screen, self._font_title, self._font_hint, "EQUIPMENT", "gear, compare, commit", PAD_X, PAD_Y)

        member_rect, slot_rect, picker_rect = self._layout(screen)
        render_panel(screen, member_rect, active=view.page_id == PAGE_MEMBER, title="Party", title_font=self._font_head)
        self._render_members(screen, member_rect, view)
        if view.page_id in (PAGE_SLOT, PAGE_PICKER):
            render_panel(screen, slot_rect, active=view.page_id == PAGE_SLOT, title="Slots", title_font=self._font_head)
            self._render_slots(screen, slot_rect, view)
        if view.page_id == PAGE_PICKER:
            render_panel(screen, picker_rect, active=True, title="Inventory", title_font=self._font_head)
            self._render_picker(screen, picker_rect, view)

        self._render_hint(screen, view.page_id)

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        bottom_pad = 62
        panel_h = max(360, sh - top - bottom_pad)
        available = sw - PAD_X * 2 - GAP * 2
        member_w = member_column_width(sw)
        slot_w = min(COL_W, max(250, available // 4))
        picker_w = max(360, available - member_w - slot_w)
        member_rect = pygame.Rect(PAD_X, top, member_w, panel_h)
        slot_rect = pygame.Rect(member_rect.right + GAP, top, slot_w, panel_h)
        picker_rect = pygame.Rect(slot_rect.right + GAP, top, picker_w, panel_h)
        return member_rect, slot_rect, picker_rect

    def _render_members(self, screen: pygame.Surface, panel: pygame.Rect, view: EquipViewState) -> None:
        render_member_column(
            screen, panel, view.members,
            selection=view.member_selection,
            active_page=view.page_id == PAGE_MEMBER,
            font_head=self._font_head,
            font_row=self._font_row,
            font_meta=self._font_meta,
        )

    def _render_slots(self, screen: pygame.Surface, panel: pygame.Rect, view: EquipViewState) -> None:
        member = view.member
        if member is None:
            return
        x = panel.x + 16
        y = panel.y + 52

        active_page = view.page_id == PAGE_SLOT
        sel = view.slot_selection
        for i, slot in enumerate(SLOTS):
            selected = (i == sel)
            item_id = member.equipped.get(slot) or ""
            label = SLOT_LABEL[slot]
            value = self._display_name(item_id) if item_id else "-"
            row = pygame.Rect(x, y + i * (ROW_H + 8), panel.w - 32, ROW_H)
            render_icon_row(
                screen,
                self._font_row,
                row,
                label,
                icon_key=f"slot_{slot}",
                focused=selected and active_page,
                dimmed_sel=selected and view.page_id == PAGE_PICKER,
                color=INK if item_id else DIM,
                right_text=value,
                right_font=self._font_meta,
                subtext=slot.title(),
                sub_font=self._font_meta,
            )

        y += len(SLOTS) * (ROW_H + 8) + 6
        draw_divider(screen, x, y, panel.w - 32)
        y += 12
        totals = stat_totals(member, self._catalog)
        stat_w = max(54, (panel.w - 46) // len(STAT_ORDER))
        for i, key in enumerate(STAT_ORDER):
            sx = x + i * stat_w
            label = self._font_meta.render(STAT_LABEL[key], True, MUTED)
            value = self._font_stat.render(str(totals[key]), True, GOLD)
            screen.blit(label, (sx, y))
            screen.blit(value, (sx, y + label.get_height() + 1))

    def _render_picker(self, screen: pygame.Surface, panel: pygame.Rect, view: EquipViewState) -> None:
        member = view.member
        if member is None:
            return
        x = panel.x + 16
        y = panel.y + 52
        slot = view.slot
        sub = self._font_meta.render(
            f"{member.name} / {SLOT_LABEL[slot]}",
            True,
            MUTED,
        )
        screen.blit(sub, (panel.right - 18 - sub.get_width(), panel.y + 19))

        if not view.picker_rows:
            msg = self._font_row.render("(none equippable)", True, C_TEXT_DIM)
            screen.blit(msg, (x, y))
            return

        row_h = ROW_H + 8
        list_w = panel.w - 32
        sel = view.picker_selection
        preview_h = 150
        visible_h = panel.bottom - y - preview_h - 18
        max_rows = max(1, visible_h // row_h)
        first = max(0, min(sel - max_rows + 1, max(0, len(view.picker_rows) - max_rows)))
        for i, row in enumerate(view.picker_rows[first:first + max_rows], start=first):
            selected = (i == sel)
            if row.item_id is None:
                label = "(Unequip)"
                color = MUTED
                icon_key = "unequip"
                subtext = "return current item to bag"
                right = ""
            else:
                label = row.item.name
                color = INK
                icon_key = f"item_{row.item.type}_{row.item.id}"
                subtext = row.item.slot_category or row.item.type
                right = _stats_summary(row.item)
            rect = pygame.Rect(x, y + (i - first) * row_h, list_w, ROW_H)
            render_icon_row(
                screen,
                self._font_row,
                rect,
                label,
                icon_key=icon_key,
                focused=selected,
                dimmed_sel=False,
                color=color,
                right_text=right,
                right_font=self._font_meta,
                subtext=subtext,
                sub_font=self._font_meta,
            )

        preview_y = panel.bottom - preview_h
        draw_divider(screen, x, preview_y - 10, list_w)
        self._render_preview(screen, x, preview_y, list_w, view)

    def _render_preview(self, screen, x, y, w, view: EquipViewState) -> None:
        row = view.picker_rows[view.picker_selection] if view.picker_rows else None
        if row is None:
            return
        current = stat_totals(view.member, self._catalog)
        after = stat_totals_preview(
            view.member, self._catalog, view.slot, row.item_id,
        )
        head = self._font_stat.render("Preview", True, C_HEAD)
        screen.blit(head, (x, y))
        y += head.get_height() + 4
        for key in STAT_ORDER:
            before = current.get(key, 0)
            now = after.get(key, 0)
            if now > before:
                marker, color = "UP", C_UP
            elif now < before:
                marker, color = "DN", C_DOWN
            else:
                marker, color = "-", C_TEXT_MUT
            line = f"{STAT_LABEL[key]:<3} {before:>3} -> {now:>3} {marker}"
            screen.blit(self._font_stat.render(line, True, color), (x, y))
            y += self._font_stat.get_height() + 2

        if row.item is not None and row.item.description:
            y += 4
            for line in wrap_text(self._font_meta, row.item.description, w, limit=2):
                desc = self._font_meta.render(line, True, MUTED)
                screen.blit(desc, (x, y))
                y += self._font_meta.get_height() + 2

    def _render_hint(self, screen: pygame.Surface, page_id: str) -> None:
        sw, sh = screen.get_size()
        hint_text = {
            PAGE_MEMBER: "UP/DOWN select member    ENTER open slots    ESC close",
            PAGE_SLOT:   "UP/DOWN select slot    ENTER change item    ESC back",
            PAGE_PICKER: "UP/DOWN preview    ENTER equip    ESC back",
        }[page_id]
        hint = self._font_hint.render(hint_text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))

    def _display_name(self, item_id: str) -> str:
        defn = self._catalog.get(item_id)
        if defn is None:
            return item_id
        return defn.name


def _stats_summary(item: ItemDef) -> str:
    chunks: list[str] = []
    for key, value in item.stats[:2]:
        label = STAT_LABEL.get(key, key.upper())
        if isinstance(value, (int, float)) and value > 0:
            chunks.append(f"{label}+{value}")
        else:
            chunks.append(f"{label}{value}")
    return " ".join(chunks)
