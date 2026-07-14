# engine/equipment/equip_scene.py
#
# Field equip scene: character → slot → item picker with before/after stat
# diff. Switched in from the field menu; ESC/M backs out a page or closes
# the scene from the first page. Built on engine.common.wizard_scene so
# nav, hover SFX, and the scene-close path are shared with SpellScene.
# Drawing lives in equip_renderer.EquipRenderer; this scene owns wizard
# state, input, and the equip/unequip operations.

from __future__ import annotations

import pygame

from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.item.item_catalog import ItemCatalog
from engine.party.member_state import MemberState
from engine.equipment.equip_renderer import (
    PAGE_MEMBER,
    PAGE_PICKER,
    PAGE_SLOT,
    SLOTS,
    EquipRenderer,
    EquipViewState,
    PickerRow,
)
from engine.equipment.equipment_logic import equip, unequip, equippable_items


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
        self._renderer = EquipRenderer(catalog)

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
        self._renderer.render(screen, EquipViewState(
            page_id=self.page_id,
            members=self._members(),
            member=self._current_member(),
            slot=self._current_slot(),
            member_selection=self._page(PAGE_MEMBER).selection,
            slot_selection=self._page(PAGE_SLOT).selection,
            picker_selection=self._page(PAGE_PICKER).selection,
            picker_rows=self._picker_rows,
        ))
