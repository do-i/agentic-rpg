# engine/status/status_scene.py
#
# Field Status screen: party → member detail → action. Built on
# engine.common.wizard_scene so navigation, hover SFX, and the scene-close
# path are shared with EquipScene / SpellScene. Drawing lives in
# status_renderer.StatusRenderer; this scene owns input, page flow, spell
# casting, and the warp/target overlays.
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

from pathlib import Path

import pygame

from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.target_select_overlay_renderer import TargetSelectOverlay
from engine.common.warp_select_overlay import WarpSelectOverlay
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.io.save_manager import GameStateManager
from engine.party.member_state import MemberState
from engine.spell.spell_logic import learned_spells, is_field_castable
from engine.status.status_logic import apply_spell, apply_spell_all, valid_targets
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
from engine.world.warp_logic import warp_destinations, WarpDestination
from engine.world.sprite_sheet import Direction


class StatusScene(WizardScene):
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
        self._holder = holder
        self._scenario_path = scenario_path
        self._game_state_manager = game_state_manager

        self._spells: list[dict] = []
        self._detail_mode: str = CAT_SPELLS
        self._target_overlay: TargetSelectOverlay | None = None
        self._warp_overlay: WarpSelectOverlay | None = None
        self._popup_text: str = ""
        self._popup_active: bool = False
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

    def _members(self) -> list[MemberState]:
        return list(self._holder.get().party.members)

    def _current_member(self) -> MemberState | None:
        members = self._members()
        if not members:
            return None
        sel = self._page(PAGE_MEMBER).selection
        return members[min(sel, len(members) - 1)]

    def _classes_dir(self) -> Path:
        return Path(self._scenario_path) / "data" / "classes"

    def _flags_set(self) -> set[str]:
        return set(self._holder.get().flags.to_list())

    def _load_spells(self) -> list[dict]:
        member = self._current_member()
        if member is None:
            return []
        return learned_spells(member, self._classes_dir(), self._flags_set())

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

    # ── Modal-overlay routing ────────────────────────────────

    def _is_input_blocked(self) -> bool:
        return (
            self._target_overlay is not None
            or self._warp_overlay is not None
            or self._popup_active
        )

    def _handle_blocked_input(self, events: list[pygame.event.Event]) -> None:
        if self._warp_overlay:
            self._warp_overlay.handle_events(events)
            return
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER,
            ):
                self._popup_active = False

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
                self._popup_text = f"{member.name} knows no spells."
                self._popup_active = True
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
        if not is_field_castable(spell):
            self._play("cancel")
            return None
        if member.mp < spell["mp_cost"]:
            self._popup_text = f"{member.name} has not enough MP."
            self._popup_active = True
            self._play("cancel")
            return None
        if spell.get("warp"):
            return self._open_warp(spell, member)
        target_type = spell.get("target")
        if target_type in ("all_allies", "party"):
            self._play("confirm")
            msg = apply_spell_all(spell, member, self._holder.get().party.members)
            self._popup_text = msg
            self._popup_active = True
            return None
        targets = valid_targets(spell, self._holder.get().party.members)
        if not targets:
            self._popup_text = "No valid targets."
            self._popup_active = True
            self._play("cancel")
            return None
        self._play("confirm")
        pending = spell
        self._target_overlay = TargetSelectOverlay(
            targets=targets,
            item_label=spell["name"],
            on_confirm=lambda t, s=pending, c=member: self._on_target_confirm(s, c, t),
            on_cancel=self._on_target_cancel,
            sfx_manager=self._sfx_manager,
        )
        return None

    # ── Teleport / target callbacks ──────────────────────────

    def _open_warp(self, spell: dict, caster: MemberState) -> str | None:
        state = self._holder.get()
        destinations = warp_destinations(state.map, Path(self._scenario_path))
        if not destinations:
            self._popup_text = "Nowhere to teleport to yet."
            self._popup_active = True
            self._play("cancel")
            return None
        self._play("confirm")
        self._warp_overlay = WarpSelectOverlay(
            destinations=destinations,
            on_confirm=lambda dest, s=spell, c=caster: self._on_warp_confirm(s, c, dest),
            on_cancel=self._on_warp_cancel,
            sfx_manager=self._sfx_manager,
        )
        return None

    def _on_warp_confirm(self, spell: dict, caster: MemberState, dest: WarpDestination) -> None:
        caster.mp = max(0, caster.mp - spell["mp_cost"])
        state = self._holder.get()
        state.map.move_to(dest.map_id, dest.position, Direction.DOWN)
        self._game_state_manager.save(state, slot_index=0)
        self._warp_overlay = None
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    def _on_warp_cancel(self) -> None:
        self._warp_overlay = None

    def _on_target_confirm(self, spell: dict, caster: MemberState, target: MemberState) -> None:
        msg = apply_spell(spell, caster, target)
        self._target_overlay = None
        self._popup_text = msg
        self._popup_active = True

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

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
        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._warp_overlay:
            self._warp_overlay.render(screen)
        if self._popup_active:
            self._renderer.render_popup(screen, self._popup_text)
