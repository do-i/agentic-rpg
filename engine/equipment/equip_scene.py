# engine/equipment/equip_scene.py
#
# Field equip scene: character → slot → item picker with before/after stat
# diff. Switched in from the field menu; ESC/M backs out a page or closes
# the scene from the first page. Built on engine.common.wizard_scene so
# nav, hover SFX, and the scene-close path are shared with SpellScene.

from __future__ import annotations

from dataclasses import dataclass

import pygame

from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.color_constants import (
    C_TEXT_MUT, C_TEXT_DIM, C_HEAD,
)
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    draw_divider,
    fit_text,
    icon_surface,
    member_icon_path,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    render_row_frame,
    wrap_text,
)
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.item.item_catalog import ItemCatalog, ItemDef
from engine.party.member_state import MemberState
from engine.equipment.equipment_logic import (
    equip, unequip, equippable_items, stat_totals, stat_totals_preview,
)


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


class EquipScene(WizardScene):
    """Field equip flow. Pages: MEMBER → SLOT → PICKER → apply."""

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        catalog: ItemCatalog,
        return_scene_name: str,
        sfx_manager,
    ) -> None:
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._holder = holder
        self._catalog = catalog
        self._picker_rows: list[PickerRow] = []
        self._fonts_ready = False

        self._register_page(WizardPage(
            name=PAGE_MEMBER,
            count_fn=lambda: len(self._members()),
            on_confirm=self._confirm_member,
            on_back=lambda: None,           # close scene
        ))
        self._register_page(WizardPage(
            name=PAGE_SLOT,
            count_fn=lambda: len(SLOTS),
            on_confirm=self._confirm_slot,
            on_back=lambda: PAGE_MEMBER,
        ))
        self._register_page(WizardPage(
            name=PAGE_PICKER,
            count_fn=lambda: len(self._picker_rows),
            on_confirm=self._confirm_picker,
            on_back=lambda: PAGE_SLOT,
        ))

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_stat  = f.get(16)
        self._font_hint  = f.get(14)
        self._font_meta  = f.get(13)
        self._fonts_ready = True

    # ── Helpers ───────────────────────────────────────────────

    def _members(self) -> list[MemberState]:
        return list(self._holder.get().party.members)

    def _current_member(self) -> MemberState | None:
        members = self._members()
        if not members:
            return None
        sel = self._page(PAGE_MEMBER).selection
        return members[min(sel, len(members) - 1)]

    def _current_slot(self) -> str:
        sel = self._page(PAGE_SLOT).selection
        return SLOTS[min(sel, len(SLOTS) - 1)]

    def _build_picker_rows(self) -> list[PickerRow]:
        member = self._current_member()
        if member is None:
            return []
        slot = self._current_slot()
        repo = self._holder.get().repository
        rows: list[PickerRow] = [PickerRow(item_id=None, item=None)]   # Unequip
        for defn in equippable_items(member, repo, self._catalog, slot):
            rows.append(PickerRow(item_id=defn.id, item=defn))
        return rows

    # ── Page confirm callbacks ───────────────────────────────

    def _confirm_member(self) -> str | None:
        self._play("confirm")
        return PAGE_SLOT

    def _confirm_slot(self) -> str | None:
        self._play("confirm")
        self._picker_rows = self._build_picker_rows()
        return PAGE_PICKER

    def _confirm_picker(self) -> str | None:
        member = self._current_member()
        if member is None or not self._picker_rows:
            return None
        sel = self._page(PAGE_PICKER).selection
        row = self._picker_rows[sel]
        slot = self._current_slot()
        repo = self._holder.get().repository
        if row.item_id is None:
            # Unequip row
            if member.equipped.get(slot):
                unequip(member, repo, slot)
                self._play("confirm")
            else:
                self._play("cancel")
        else:
            try:
                equip(member, repo, self._catalog, row.item_id)
                self._play("confirm")
            except ValueError:
                self._play("cancel")
                return None
        return PAGE_SLOT

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        render_backdrop(screen)
        render_header(screen, self._font_title, self._font_hint, "EQUIPMENT", "gear, compare, commit", PAD_X, PAD_Y)

        member_rect, slot_rect, picker_rect = self._layout(screen)
        render_panel(screen, member_rect, active=self.page_id == PAGE_MEMBER, title="Party", title_font=self._font_head)
        self._render_members(screen, member_rect)
        if self.page_id in (PAGE_SLOT, PAGE_PICKER):
            render_panel(screen, slot_rect, active=self.page_id == PAGE_SLOT, title="Slots", title_font=self._font_head)
            self._render_slots(screen, slot_rect)
        if self.page_id == PAGE_PICKER:
            render_panel(screen, picker_rect, active=True, title="Inventory", title_font=self._font_head)
            self._render_picker(screen, picker_rect)

        self._render_hint(screen)

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        bottom_pad = 62
        panel_h = max(360, sh - top - bottom_pad)
        available = sw - PAD_X * 2 - GAP * 2
        member_w = min(COL_W, max(245, available // 4))
        slot_w = min(COL_W, max(250, available // 4))
        picker_w = max(360, available - member_w - slot_w)
        member_rect = pygame.Rect(PAD_X, top, member_w, panel_h)
        slot_rect = pygame.Rect(member_rect.right + GAP, top, slot_w, panel_h)
        picker_rect = pygame.Rect(slot_rect.right + GAP, top, picker_w, panel_h)
        return member_rect, slot_rect, picker_rect

    def _render_members(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        members = self._members()
        x = panel.x + 16
        top = panel.y + 52
        w = panel.w - 32
        if not members:
            msg = self._font_row.render("No members.", True, C_TEXT_DIM)
            screen.blit(msg, (x, top))
            return
        sel = self._page(PAGE_MEMBER).selection
        active_page = self.page_id == PAGE_MEMBER

        # Distribute member cards down the full panel height so portraits can
        # grow into the vertical space the shared 36px icon row leaves empty.
        n = len(members)
        gap = 14
        avail = (panel.bottom - 16) - top
        row_h = min(118, (avail - gap * (n - 1)) // n)
        portrait = min(row_h - 16, 92)

        for i, m in enumerate(members):
            selected = (i == sel)
            row = pygame.Rect(x, top + i * (row_h + gap), w, row_h)
            self._render_member_card(
                screen, row, m, portrait,
                focused=selected and active_page,
                dimmed=selected and not active_page,
            )

    def _render_member_card(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        m: MemberState,
        portrait: int,
        *,
        focused: bool,
        dimmed: bool,
    ) -> None:
        render_row_frame(screen, rect, focused=focused, dimmed_sel=dimmed)

        icon = icon_surface(
            f"member_{m.id}", portrait, image_path=member_icon_path(m.id),
        )
        screen.blit(icon, (rect.x + 12, rect.y + (rect.h - portrait) // 2))

        tx = rect.x + 24 + portrait
        max_w = rect.right - tx - 14
        name = fit_text(self._font_head, f"{m.name}  Lv{m.level}", INK, max_w)
        cls = fit_text(self._font_row, m.class_name.title(), GOLD, max_w)
        hp = self._font_meta.render(f"HP {m.hp}/{m.hp_max}", True, MUTED)
        mp = self._font_meta.render(f"MP {m.mp}/{m.mp_max}", True, MUTED)

        line_gap = 6
        block_h = (
            name.get_height() + line_gap
            + cls.get_height() + line_gap
            + max(hp.get_height(), mp.get_height())
        )
        ty = rect.y + (rect.h - block_h) // 2
        screen.blit(name, (tx, ty))
        ty += name.get_height() + line_gap
        screen.blit(cls, (tx, ty))
        ty += cls.get_height() + line_gap
        screen.blit(hp, (tx, ty))
        screen.blit(mp, (tx + max(hp.get_width() + 18, 96), ty))

    def _render_slots(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        member = self._current_member()
        if member is None:
            return
        x = panel.x + 16
        y = panel.y + 52

        active_page = self.page_id == PAGE_SLOT
        sel = self._page(PAGE_SLOT).selection
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
                dimmed_sel=selected and self.page_id == PAGE_PICKER,
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

    def _render_picker(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        member = self._current_member()
        if member is None:
            return
        x = panel.x + 16
        y = panel.y + 52
        slot = self._current_slot()
        sub = self._font_meta.render(
            f"{member.name} / {SLOT_LABEL[slot]}",
            True,
            MUTED,
        )
        screen.blit(sub, (panel.right - 18 - sub.get_width(), panel.y + 19))

        if not self._picker_rows:
            msg = self._font_row.render("(none equippable)", True, C_TEXT_DIM)
            screen.blit(msg, (x, y))
            return

        row_h = ROW_H + 8
        list_w = panel.w - 32
        sel = self._page(PAGE_PICKER).selection
        preview_h = 150
        visible_h = panel.bottom - y - preview_h - 18
        max_rows = max(1, visible_h // row_h)
        first = max(0, min(sel - max_rows + 1, max(0, len(self._picker_rows) - max_rows)))
        for i, row in enumerate(self._picker_rows[first:first + max_rows], start=first):
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
        self._render_preview(screen, x, preview_y, list_w, member, slot)

    def _render_preview(self, screen, x, y, w, member, slot) -> None:
        sel = self._page(PAGE_PICKER).selection
        row = self._picker_rows[sel] if self._picker_rows else None
        if row is None:
            return
        current = stat_totals(member, self._catalog)
        after = stat_totals_preview(
            member, self._catalog, slot, row.item_id,
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

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        hint_text = {
            PAGE_MEMBER: "UP/DOWN select member    ENTER open slots    ESC close",
            PAGE_SLOT:   "UP/DOWN select slot    ENTER change item    ESC back",
            PAGE_PICKER: "UP/DOWN preview    ENTER equip    ESC back",
        }[self.page_id]
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
