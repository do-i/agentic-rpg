# engine/spell/spell_scene.py
#
# Field Menu Spells screen: character picker -> learned spells list
# -> target select for field-castable spells (heal/cure/buff).
# Battle-only spells appear as inspect-only rows.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.color_constants import (
    C_BG, C_TEXT, C_TEXT_MUT, C_TEXT_DIM, C_HEAD,
)
from engine.common.menu_popup import render_popup
from engine.common.menu_row_renderer import render_row
from engine.common.target_select_overlay_renderer import TargetSelectOverlay
from engine.party.member_state import MemberState
from engine.spell.spell_logic import learned_spells, is_field_castable
from engine.status.status_logic import apply_spell, apply_spell_all, valid_targets


PAGE_MEMBER = "member"
PAGE_SPELL  = "spell"

C_BADGE   = (120, 120, 160)

PAD_X = 30
PAD_Y = 24
COL_W = 260


class SpellScene(Scene):
    """Field spell browser with optional casting.

    Pages: MEMBER -> SPELL. Castable spells open a target overlay. Battle-only
    spells are rendered in a dimmed color and produce a 'cancel' beep on ENTER.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str,
        return_scene_name: str,
        sfx_manager,
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._scenario_path = scenario_path
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager

        self._page = PAGE_MEMBER
        self._member_sel = 0
        self._spell_sel  = 0
        self._spells: list[dict] = []

        self._target_overlay: TargetSelectOverlay | None = None
        self._popup_text: str = ""
        self._popup_active: bool = False
        self._fonts_ready = False

    def set_return_scene(self, name: str) -> None:
        self._return_scene_name = name

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_meta  = f.get(14)
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

    def _classes_dir(self) -> Path:
        return Path(self._scenario_path) / "data" / "classes"

    def _flags_set(self) -> set[str]:
        return set(self._holder.get().flags.to_list())

    def _load_spells(self) -> list[dict]:
        member = self._current_member()
        if member is None:
            return []
        return learned_spells(member, self._classes_dir(), self._flags_set())

    def _play(self, key: str) -> None:
        if self._sfx_manager:
            self._sfx_manager.play(key)

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return
        if self._popup_active:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER,
                ):
                    self._popup_active = False
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._page == PAGE_MEMBER:
                self._handle_member(event.key)
            elif self._page == PAGE_SPELL:
                self._handle_spell(event.key)

    def _handle_member(self, key: int) -> None:
        members = self._members()
        if key in (pygame.K_ESCAPE, pygame.K_m):
            self._close()
        elif key == pygame.K_UP and members:
            self._set_member_sel(max(0, self._member_sel - 1))
        elif key == pygame.K_DOWN and members:
            self._set_member_sel(min(len(members) - 1, self._member_sel + 1))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and members:
            self._spells = self._load_spells()
            if not self._spells:
                member = self._current_member()
                self._popup_text = f"{member.name} has no spells."
                self._popup_active = True
                self._play("cancel")
                return
            self._play("confirm")
            self._spell_sel = 0
            self._page = PAGE_SPELL

    def _handle_spell(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_m):
            self._play("cancel")
            self._page = PAGE_MEMBER
            return
        if not self._spells:
            return
        if key == pygame.K_UP:
            self._set_spell_sel(max(0, self._spell_sel - 1))
        elif key == pygame.K_DOWN:
            self._set_spell_sel(min(len(self._spells) - 1, self._spell_sel + 1))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm_spell()

    def _confirm_spell(self) -> None:
        spell = self._spells[self._spell_sel]
        caster = self._current_member()
        if caster is None:
            return
        if not is_field_castable(spell):
            self._play("cancel")
            return
        if caster.mp < spell["mp_cost"]:
            self._popup_text = f"{caster.name} has not enough MP."
            self._popup_active = True
            self._play("cancel")
            return
        target_type = spell.get("target")
        if target_type in ("all_allies", "party"):
            self._play("confirm")
            msg = apply_spell_all(spell, caster, self._holder.get().party.members)
            self._popup_text = msg
            self._popup_active = True
            return
        targets = valid_targets(spell, self._holder.get().party.members)
        if not targets:
            self._popup_text = "No valid targets."
            self._popup_active = True
            self._play("cancel")
            return
        self._play("confirm")
        pending = spell
        self._target_overlay = TargetSelectOverlay(
            targets=targets,
            item_label=spell["name"],
            on_confirm=lambda t, s=pending, c=caster: self._on_target_confirm(s, c, t),
            on_cancel=self._on_target_cancel,
            sfx_manager=self._sfx_manager,
        )

    def _on_target_confirm(self, spell: dict, caster: MemberState, target: MemberState) -> None:
        msg = apply_spell(spell, caster, target)
        self._target_overlay = None
        self._popup_text = msg
        self._popup_active = True

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    def _set_member_sel(self, new: int) -> None:
        if new != self._member_sel:
            self._play("hover")
        self._member_sel = new

    def _set_spell_sel(self, new: int) -> None:
        if new != self._spell_sel:
            self._play("hover")
        self._spell_sel = new

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
        title = self._font_title.render("SPELLS", True, C_HEAD)
        screen.blit(title, (PAD_X, PAD_Y))

        self._render_members(screen)
        if self._page == PAGE_SPELL:
            self._render_spells(screen)

        self._render_hint(screen)

        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._popup_active:
            self._render_popup(screen)

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
            focused = selected and active_page
            mp_hint = f"MP {m.mp}/{m.mp_max}"
            text = f"{m.name}  Lv{m.level}  {m.class_name}  {mp_hint}"
            render_row(
                screen, self._font_row, x, y, COL_W - 16, text,
                focused,
                selected and not active_page,
                C_TEXT,
            )
            y += row_h

    def _render_spells(self, screen: pygame.Surface) -> None:
        member = self._current_member()
        if member is None:
            return
        x = PAD_X + COL_W
        y = PAD_Y + 40
        head = self._font_head.render(
            f"{member.name}'s Spells", True, C_HEAD,
        )
        screen.blit(head, (x, y))
        y += head.get_height() + 6

        row_h = self._font_row.get_height() + 12
        list_w = screen.get_width() - x - PAD_X

        for i, spell in enumerate(self._spells):
            selected = (i == self._spell_sel)
            castable = is_field_castable(spell)
            can_afford = member.mp >= spell["mp_cost"]
            if castable and can_afford:
                color = C_TEXT
            elif castable:
                color = C_TEXT_MUT
            else:
                color = C_TEXT_DIM

            mp_cost = spell["mp_cost"]
            badge = "" if castable else "  [battle]"
            line = f"{spell['name']:<20}  MP {mp_cost:>3}{badge}"
            render_row(
                screen, self._font_row, x, y, list_w - 16, line,
                selected, False, color,
            )
            y += row_h

        if self._spells:
            y += 8
            desc = self._spells[self._spell_sel].get("description", "")
            if desc:
                text = self._font_meta.render(desc, True, C_TEXT_MUT)
                screen.blit(text, (x, y))

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        if self._page == PAGE_MEMBER:
            text = "UP/DOWN select member    ENTER view spells    ESC close"
        else:
            text = "UP/DOWN select spell    ENTER cast    ESC back"
        hint = self._font_hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))

    def _render_popup(self, screen: pygame.Surface) -> None:
        render_popup(
            screen, self._font_row, self._font_meta, self._popup_text,
        )
