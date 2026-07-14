# engine/spell/field_cast_mixin.py
#
# Field spell casting flow shared by SpellScene and StatusScene: the
# castability/MP checks, the warp and target overlays, the result popup,
# and the blocked-input routing WizardScene consults. Host scenes stay
# responsible for page flow and for picking which spell to cast.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.target_select_overlay_renderer import TargetSelectOverlay
from engine.common.warp_select_overlay import WarpSelectOverlay
from engine.party.member_state import MemberState
from engine.spell.spell_logic import learned_spells, is_field_castable
from engine.spell.spell_renderer import PAGE_MEMBER
from engine.status.status_logic import apply_spell, apply_spell_all, valid_targets
from engine.world.warp_logic import warp_destinations, WarpDestination
from engine.world.sprite_sheet import Direction


class FieldCastMixin:
    """Mix into a WizardScene with a PAGE_MEMBER ("member") page.

    Hosts call `_init_field_cast` in __init__, route ENTER on a spell row
    to `_cast_spell`, and call `_render_field_cast_overlays` at the end of
    their render(). Everything else (overlay callbacks, popup dismissal,
    input blocking) is handled here.
    """

    def _init_field_cast(
        self,
        holder,
        scenario_path: str,
        game_state_manager,
    ) -> None:
        self._holder = holder
        self._scenario_path = scenario_path
        self._game_state_manager = game_state_manager
        self._spells: list[dict] = []
        self._target_overlay: TargetSelectOverlay | None = None
        self._warp_overlay: WarpSelectOverlay | None = None
        self._popup_text: str = ""
        self._popup_active: bool = False

    # ── Shared party/spell helpers ───────────────────────────

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

    def _show_popup(self, text: str) -> None:
        self._popup_text = text
        self._popup_active = True

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

    # ── Casting flow ─────────────────────────────────────────

    def _cast_spell(self, spell: dict, caster: MemberState) -> str | None:
        """ENTER on a spell row: cast if field-castable, else beep.

        Party-wide spells apply immediately; warp spells open the
        destination picker; single-target spells open the target overlay.
        """
        if not is_field_castable(spell):
            self._play("cancel")
            return None
        if caster.mp < spell["mp_cost"]:
            self._show_popup(f"{caster.name} has not enough MP.")
            self._play("cancel")
            return None
        if spell.get("warp"):
            return self._open_warp(spell, caster)
        target_type = spell.get("target")
        if target_type in ("all_allies", "party"):
            self._play("confirm")
            msg = apply_spell_all(spell, caster, self._holder.get().party.members)
            self._show_popup(msg)
            return None
        targets = valid_targets(spell, self._holder.get().party.members)
        if not targets:
            self._show_popup("No valid targets.")
            self._play("cancel")
            return None
        self._play("confirm")
        pending = spell
        self._target_overlay = TargetSelectOverlay(
            targets=targets,
            item_label=spell["name"],
            on_confirm=lambda t, s=pending, c=caster: self._on_target_confirm(s, c, t),
            on_cancel=self._on_target_cancel,
            sfx_manager=self._sfx_manager,
        )
        return None

    def _open_warp(self, spell: dict, caster: MemberState) -> str | None:
        """Open the teleport destination picker for a `warp` utility spell.

        MP is only spent once a destination is confirmed (in _on_warp_confirm),
        so cancelling out costs nothing.
        """
        state = self._holder.get()
        destinations = warp_destinations(state.map, Path(self._scenario_path))
        if not destinations:
            self._show_popup("Nowhere to teleport to yet.")
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
        """Spend MP, move the party to the chosen destination, and return to
        the world map. The persistent WorldMapScene reloads when it notices
        state.map.current changed (see WorldMapScene._ensure_init)."""
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
        self._show_popup(msg)

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    # ── Render ────────────────────────────────────────────────

    def _render_field_cast_overlays(self, screen: pygame.Surface) -> None:
        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._warp_overlay:
            self._warp_overlay.render(screen)
        if self._popup_active:
            self._renderer.render_popup(screen, self._popup_text)
