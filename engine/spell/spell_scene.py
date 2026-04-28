# engine/spell/spell_scene.py
#
# Field Menu Spells screen: character picker → learned spells list → target
# select for field-castable spells (heal/cure/buff). Battle-only spells
# appear as inspect-only rows. Built on engine.common.wizard_scene.

from __future__ import annotations

from pathlib import Path

import pygame

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
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.party.member_state import MemberState
from engine.spell.spell_logic import learned_spells, is_field_castable
from engine.status.status_logic import apply_spell, apply_spell_all, valid_targets


PAGE_MEMBER = "member"
PAGE_SPELL  = "spell"

C_BADGE = (120, 120, 160)

PAD_X = 30
PAD_Y = 24
COL_W = 260


class SpellScene(WizardScene):
    """Field spell browser with optional casting.

    Pages: MEMBER → SPELL. Castable spells open a target overlay. Battle-only
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
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._holder = holder
        self._scenario_path = scenario_path
        self._spells: list[dict] = []
        self._target_overlay: TargetSelectOverlay | None = None
        self._popup_text: str = ""
        self._popup_active: bool = False
        self._fonts_ready = False

        self._register_page(WizardPage(
            name=PAGE_MEMBER,
            count_fn=lambda: len(self._members()),
            on_confirm=self._confirm_member,
            on_back=lambda: None,           # close scene
        ))
        self._register_page(WizardPage(
            name=PAGE_SPELL,
            count_fn=lambda: len(self._spells),
            on_confirm=self._confirm_spell,
            on_back=lambda: PAGE_MEMBER,
        ))

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

    # ── Modal-overlay routing ────────────────────────────────

    def _is_input_blocked(self) -> bool:
        return self._target_overlay is not None or self._popup_active

    def _handle_blocked_input(self, events: list[pygame.event.Event]) -> None:
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
        self._spells = self._load_spells()
        if not self._spells:
            member = self._current_member()
            self._popup_text = f"{member.name} has no spells."
            self._popup_active = True
            self._play("cancel")
            return None
        self._play("confirm")
        return PAGE_SPELL

    def _confirm_spell(self) -> str | None:
        sel = self._page(PAGE_SPELL).selection
        spell = self._spells[sel]
        caster = self._current_member()
        if caster is None:
            return None
        if not is_field_castable(spell):
            self._play("cancel")
            return None
        if caster.mp < spell["mp_cost"]:
            self._popup_text = f"{caster.name} has not enough MP."
            self._popup_active = True
            self._play("cancel")
            return None
        target_type = spell.get("target")
        if target_type in ("all_allies", "party"):
            self._play("confirm")
            msg = apply_spell_all(spell, caster, self._holder.get().party.members)
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
            on_confirm=lambda t, s=pending, c=caster: self._on_target_confirm(s, c, t),
            on_cancel=self._on_target_cancel,
            sfx_manager=self._sfx_manager,
        )
        return None

    def _on_target_confirm(self, spell: dict, caster: MemberState, target: MemberState) -> None:
        msg = apply_spell(spell, caster, target)
        self._target_overlay = None
        self._popup_text = msg
        self._popup_active = True

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(C_BG)
        title = self._font_title.render("SPELLS", True, C_HEAD)
        screen.blit(title, (PAD_X, PAD_Y))

        self._render_members(screen)
        if self.page_id == PAGE_SPELL:
            self._render_spells(screen)

        self._render_hint(screen)

        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._popup_active:
            render_popup(
                screen, self._font_row, self._font_meta, self._popup_text,
            )

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
        sel = self._page(PAGE_MEMBER).selection
        active_page = self.page_id == PAGE_MEMBER
        for i, m in enumerate(members):
            selected = (i == sel)
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
        sel = self._page(PAGE_SPELL).selection

        for i, spell in enumerate(self._spells):
            selected = (i == sel)
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
            desc = self._spells[sel].get("description", "")
            if desc:
                text = self._font_meta.render(desc, True, C_TEXT_MUT)
                screen.blit(text, (x, y))

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        if self.page_id == PAGE_MEMBER:
            text = "UP/DOWN select member    ENTER view spells    ESC close"
        else:
            text = "UP/DOWN select spell    ENTER cast    ESC back"
        hint = self._font_hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))
