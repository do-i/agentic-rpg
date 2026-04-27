# engine/equipment/equip_scene.py
#
# Field equip scene: character -> slot -> item picker with before/after
# stat diff. Switched in from the field menu; ESC/M back to field_menu.

from __future__ import annotations

from dataclasses import dataclass

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.color_constants import (
    C_BG, C_TEXT, C_TEXT_MUT, C_TEXT_DIM, C_HEAD,
)
from engine.common.menu_row_renderer import render_row
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

C_UP        = (120, 220, 120)
C_DOWN      = (220, 110, 110)

PAD_X      = 30
PAD_Y      = 24
COL_W      = 260


@dataclass
class PickerRow:
    item_id: str | None      # None = Unequip row
    item: ItemDef | None     # None for Unequip row


class EquipScene(Scene):
    """Field equip flow. Pages: MEMBER -> SLOT -> PICKER -> apply."""

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        catalog: ItemCatalog,
        return_scene_name: str,
        sfx_manager,
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._catalog = catalog
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager

        self._page = PAGE_MEMBER
        self._member_sel = 0
        self._slot_sel = 0
        self._item_sel = 0
        self._picker_rows: list[PickerRow] = []
        self._fonts_ready = False

    def set_return_scene(self, name: str) -> None:
        self._return_scene_name = name

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_stat  = f.get(16)
        self._font_hint  = f.get(14)
        self._fonts_ready = True

    # ── Helpers ───────────────────────────────────────────────

    def _members(self) -> list[MemberState]:
        return list(self._holder.get().party.members)

    def _current_member(self) -> MemberState | None:
        members = self._members()
        if not members:
            return None
        return members[min(self._member_sel, len(members) - 1)]

    def _current_slot(self) -> str:
        return SLOTS[min(self._slot_sel, len(SLOTS) - 1)]

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

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._page == PAGE_MEMBER:
                self._handle_member(event.key)
            elif self._page == PAGE_SLOT:
                self._handle_slot(event.key)
            elif self._page == PAGE_PICKER:
                self._handle_picker(event.key)

    def _handle_member(self, key: int) -> None:
        members = self._members()
        if key in (pygame.K_ESCAPE, pygame.K_m):
            self._close()
        elif key == pygame.K_UP and members:
            self._set_member_sel(max(0, self._member_sel - 1))
        elif key == pygame.K_DOWN and members:
            self._set_member_sel(min(len(members) - 1, self._member_sel + 1))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and members:
            self._play("confirm")
            self._page = PAGE_SLOT
            self._slot_sel = 0

    def _handle_slot(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_m):
            self._play("cancel")
            self._page = PAGE_MEMBER
        elif key == pygame.K_UP:
            self._set_slot_sel(max(0, self._slot_sel - 1))
        elif key == pygame.K_DOWN:
            self._set_slot_sel(min(len(SLOTS) - 1, self._slot_sel + 1))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._play("confirm")
            self._picker_rows = self._build_picker_rows()
            self._item_sel = 0
            self._page = PAGE_PICKER

    def _handle_picker(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_m):
            self._play("cancel")
            self._page = PAGE_SLOT
        elif key == pygame.K_UP:
            self._set_item_sel(max(0, self._item_sel - 1))
        elif key == pygame.K_DOWN:
            self._set_item_sel(min(len(self._picker_rows) - 1, self._item_sel + 1))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._apply_selection()

    def _set_member_sel(self, new: int) -> None:
        if new != self._member_sel:
            self._play("hover")
        self._member_sel = new

    def _set_slot_sel(self, new: int) -> None:
        if new != self._slot_sel:
            self._play("hover")
        self._slot_sel = new

    def _set_item_sel(self, new: int) -> None:
        if new != self._item_sel:
            self._play("hover")
        self._item_sel = new

    def _apply_selection(self) -> None:
        member = self._current_member()
        if member is None:
            return
        if not self._picker_rows:
            return
        row = self._picker_rows[self._item_sel]
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
                return
        self._page = PAGE_SLOT

    def _play(self, key: str) -> None:
        if self._sfx_manager:
            self._sfx_manager.play(key)

    def _close(self) -> None:
        self._play("cancel")
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        screen.fill(C_BG)
        title = self._font_title.render("EQUIPMENT", True, C_HEAD)
        screen.blit(title, (PAD_X, PAD_Y))

        self._render_members(screen)
        if self._page in (PAGE_SLOT, PAGE_PICKER):
            self._render_slots(screen)
        if self._page == PAGE_PICKER:
            self._render_picker(screen)

        self._render_hint(screen)

    def _render_members(self, screen: pygame.Surface) -> None:
        members = self._members()
        x = PAD_X
        y = PAD_Y + 40
        head = self._font_head.render("Party", True, C_HEAD)
        screen.blit(head, (x, y))
        y += head.get_height() + 6
        if not members:
            msg = self._font_row.render("No members.", True, C_TEXT_DIM)
            screen.blit(msg, (x, y))
            return
        row_h = self._font_row.get_height() + 10
        active_page = self._page == PAGE_MEMBER
        for i, m in enumerate(members):
            selected = (i == self._member_sel)
            render_row(
                screen, self._font_row, x, y, COL_W - 16,
                f"{m.name}  Lv{m.level}  {m.class_name}",
                selected and active_page,
                selected and not active_page,
                C_TEXT,
            )
            y += row_h

    def _render_slots(self, screen: pygame.Surface) -> None:
        member = self._current_member()
        if member is None:
            return
        x = PAD_X + COL_W
        y = PAD_Y + 40
        head = self._font_head.render("Slots", True, C_HEAD)
        screen.blit(head, (x, y))
        y += head.get_height() + 6

        row_h = self._font_row.get_height() + 10
        active_page = self._page == PAGE_SLOT
        for i, slot in enumerate(SLOTS):
            selected = (i == self._slot_sel)
            item_id = member.equipped.get(slot) or ""
            label = SLOT_LABEL[slot]
            value = self._display_name(item_id) if item_id else "-"
            text = f"{label:<10} {value}"
            render_row(
                screen, self._font_row, x, y, COL_W - 16,
                text,
                selected and active_page,
                selected and self._page == PAGE_PICKER,
                C_TEXT if item_id else C_TEXT_DIM,
            )
            y += row_h

        # Current stat totals for context
        y += 8
        totals = stat_totals(member, self._catalog)
        line = "  ".join(f"{STAT_LABEL[k]} {totals[k]}" for k in STAT_ORDER)
        screen.blit(self._font_stat.render(line, True, C_TEXT_MUT), (x, y))

    def _render_picker(self, screen: pygame.Surface) -> None:
        member = self._current_member()
        if member is None:
            return
        x = PAD_X + COL_W * 2
        y = PAD_Y + 40
        slot = self._current_slot()
        head = self._font_head.render(
            f"Pick {SLOT_LABEL[slot]}", True, C_HEAD,
        )
        screen.blit(head, (x, y))
        y += head.get_height() + 6

        if not self._picker_rows:
            msg = self._font_row.render("(none equippable)", True, C_TEXT_DIM)
            screen.blit(msg, (x, y))
            return

        row_h = self._font_row.get_height() + 10
        picker_w = screen.get_width() - x - PAD_X
        for i, row in enumerate(self._picker_rows):
            selected = (i == self._item_sel)
            if row.item_id is None:
                label = "(Unequip)"
                color = C_TEXT_MUT
            else:
                label = row.item.name
                color = C_TEXT
            render_row(screen, self._font_row, x, y, picker_w - 16,
                       label, selected, False, color)
            y += row_h

        y += 8
        self._render_preview(screen, x, y, picker_w, member, slot)

    def _render_preview(self, screen, x, y, w, member, slot) -> None:
        row = self._picker_rows[self._item_sel] if self._picker_rows else None
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
            arrow = "→"
            if now > before:
                marker, color = "▲", C_UP
            elif now < before:
                marker, color = "▼", C_DOWN
            else:
                marker, color = "-", C_TEXT_MUT
            line = f"{STAT_LABEL[key]:<3} {before:>3} {arrow} {now:>3} {marker}"
            screen.blit(self._font_stat.render(line, True, color), (x, y))
            y += self._font_stat.get_height() + 2

        if row.item is not None and row.item.description:
            y += 6
            desc = self._font_stat.render(row.item.description, True, C_TEXT_MUT)
            screen.blit(desc, (x, y))

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        hint_text = {
            PAGE_MEMBER: "UP/DOWN select member    ENTER open slots    ESC close",
            PAGE_SLOT:   "UP/DOWN select slot    ENTER change item    ESC back",
            PAGE_PICKER: "UP/DOWN preview    ENTER equip    ESC back",
        }[self._page]
        hint = self._font_hint.render(hint_text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))

    def _display_name(self, item_id: str) -> str:
        defn = self._catalog.get(item_id)
        if defn is None:
            return item_id
        return defn.name
