# engine/status/status_scene.py
#
# Field Status screen: party → member detail → action. Built on
# engine.common.wizard_scene so navigation, hover SFX, and the scene-close
# path are shared with EquipScene / SpellScene. Drawing lives in
# status_renderer.StatusRenderer; the spell casting flow (MP checks,
# warp/target overlays, popup) comes from FieldCastMixin, shared with
# SpellScene. This scene owns input and page flow.
#
# Pages:
#   MEMBER   (col 1) — party roster cards; col 2 shows the selected portrait,
#                      col 3 shows backstory/persona.
#   CATEGORY (col 2) — selected member's detailed stats, plus a small action
#                      menu (Spells / Position), shown after ENTER.
#   DETAIL   (col 3) — content of the chosen action:
#                        Spells   → learned spells; field-castable ones cast
#                                   (heal/buff via target overlay, teleport via
#                                   warp picker), battle-only are inspect-only.
#                        Position → set the member's battle row (front/back).

from __future__ import annotations

import pygame

from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.io.save_manager import GameStateManager
from engine.spell.field_cast_mixin import FieldCastMixin
from engine.status.status_renderer import (
    CAT_POSITION,
    CAT_SPELLS,
    CATEGORIES,
    PAGE_CATEGORY,
    PAGE_DETAIL,
    PAGE_MEMBER,
    ROWS,
    StatusRenderer,
)


class StatusScene(FieldCastMixin, WizardScene):
    """Field party inspector. Pages: MEMBER → CATEGORY → DETAIL."""

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str = "",
        return_scene_name: str = "world_map",
        *,
        sfx_manager,
        game_state_manager: GameStateManager,
    ) -> None:
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._init_field_cast(holder, scenario_path, game_state_manager)
        self._detail_mode: str = CAT_SPELLS
        self._renderer = StatusRenderer()

        self._register_page(WizardPage(
            name=PAGE_MEMBER,
            count_fn=lambda: len(self._members()),
            on_confirm=self._confirm_member,
            on_back=lambda: None,            # close scene
        ))
        self._register_page(WizardPage(
            name=PAGE_CATEGORY,
            count_fn=lambda: len(CATEGORIES),
            on_confirm=self._confirm_category,
            on_back=lambda: PAGE_MEMBER,
        ))
        self._register_page(WizardPage(
            name=PAGE_DETAIL,
            count_fn=self._detail_count,
            on_confirm=self._confirm_detail,
            on_back=lambda: PAGE_CATEGORY,
        ))

    # ── Helpers ───────────────────────────────────────────────

    def _selected_category(self) -> str:
        return CATEGORIES[self._page(PAGE_CATEGORY).selection][0]

    def _display_name(self, item_id: str) -> str:
        catalog = self._holder.get().repository.catalog
        if catalog is not None:
            defn = catalog.get(item_id)
            if defn is not None:
                return defn.name
        return item_id.replace("_", " ").title()

    def _detail_count(self) -> int:
        if self._detail_mode == CAT_SPELLS:
            return len(self._spells)
        return len(ROWS)

    # ── Page confirm callbacks ───────────────────────────────

    def _confirm_member(self) -> str | None:
        if self._current_member() is None:
            return None
        self._play("confirm")
        return PAGE_CATEGORY

    def _confirm_category(self) -> str | None:
        cat = self._selected_category()
        if cat == CAT_SPELLS:
            self._spells = self._load_spells()
            if not self._spells:
                member = self._current_member()
                self._show_popup(f"{member.name} knows no spells.")
                self._play("cancel")
                return None
            self._detail_mode = CAT_SPELLS
        else:
            self._detail_mode = CAT_POSITION
        self._play("confirm")
        return PAGE_DETAIL

    def _confirm_detail(self) -> str | None:
        if self._detail_mode == CAT_POSITION:
            return self._confirm_position()
        return self._confirm_spell()

    def _confirm_position(self) -> str | None:
        member = self._current_member()
        if member is None:
            return None
        new_row = ROWS[self._page(PAGE_DETAIL).selection][0]
        if member.row == new_row:
            self._play("cancel")
            return None
        member.row = new_row
        self._play("confirm")
        return None

    def _confirm_spell(self) -> str | None:
        member = self._current_member()
        if member is None or not self._spells:
            return None
        spell = self._spells[self._page(PAGE_DETAIL).selection]
        return self._cast_spell(spell, member)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen,
            page_id=self.page_id,
            members=self._members(),
            member=self._current_member(),
            member_selection=self._page(PAGE_MEMBER).selection,
            category_selection=self._page(PAGE_CATEGORY).selection,
            detail_selection=self._page(PAGE_DETAIL).selection,
            detail_mode=self._detail_mode,
            spells=self._spells,
            display_name=self._display_name,
        )
        self._render_field_cast_overlays(screen)
