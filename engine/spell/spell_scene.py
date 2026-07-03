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
from engine.io.save_manager import GameStateManager
from engine.world.warp_logic import warp_destinations, WarpDestination
from engine.world.sprite_sheet import Direction
from engine.common.warp_select_overlay import WarpSelectOverlay
from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.color_constants import (
    C_TEXT_DIM,
)
from engine.common.ui.theme import DIM, EMBER, GOLD, INK, MUTED, TEAL
from engine.common.ui.chrome import (
    draw_divider,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    wrap_text,
)
from engine.common.member_card import member_column_width, render_member_column
from engine.common.menu_popup import render_popup
from engine.common.target_select_overlay_renderer import TargetSelectOverlay
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.party.member_state import MemberState
from engine.spell.spell_logic import learned_spells, is_field_castable
from engine.status.status_logic import apply_spell, apply_spell_all, valid_targets


PAGE_MEMBER = "member"
PAGE_SPELL  = "spell"

PAD_X = 40
PAD_Y = 30
GAP = 18
ROW_H = 58


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
        game_state_manager: GameStateManager,
    ) -> None:
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._holder = holder
        self._scenario_path = scenario_path
        self._game_state_manager = game_state_manager
        self._spells: list[dict] = []
        self._target_overlay: TargetSelectOverlay | None = None
        self._warp_overlay: WarpSelectOverlay | None = None
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
        self._font_meta  = f.get(CAPTION)
        self._font_hint  = f.get(14)
        self._font_small = f.get(CAPTION)
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
        if spell.get("warp"):
            return self._open_warp(spell, caster)
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

    def _open_warp(self, spell: dict, caster: MemberState) -> str | None:
        """Open the teleport destination picker for a `warp` utility spell.

        MP is only spent once a destination is confirmed (in _on_warp_confirm),
        so cancelling out costs nothing.
        """
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
        self._popup_text = msg
        self._popup_active = True

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)
        render_header(screen, self._font_title, self._font_hint, "SPELLS", "field magic and forbidden arts", PAD_X, PAD_Y)

        member_rect, spell_rect = self._layout(screen)
        render_panel(screen, member_rect, active=self.page_id == PAGE_MEMBER, title="Casters", title_font=self._font_head)
        self._render_members(screen, member_rect)
        render_panel(screen, spell_rect, active=self.page_id == PAGE_SPELL, title="Spellbook", title_font=self._font_head)
        if self.page_id == PAGE_SPELL:
            self._render_spells(screen, spell_rect)
        else:
            self._render_spellbook_idle(screen, spell_rect)

        self._render_hint(screen)

        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._warp_overlay:
            self._warp_overlay.render(screen)
        if self._popup_active:
            render_popup(
                screen, self._font_row, self._font_meta, self._popup_text,
            )

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        panel_h = max(360, sh - top - 62)
        member_w = member_column_width(sw)
        spell_w = sw - PAD_X * 2 - GAP - member_w
        member_rect = pygame.Rect(PAD_X, top, member_w, panel_h)
        spell_rect = pygame.Rect(member_rect.right + GAP, top, spell_w, panel_h)
        return member_rect, spell_rect

    def _render_members(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        render_member_column(
            screen, panel, self._members(),
            selection=self._page(PAGE_MEMBER).selection,
            active_page=self.page_id == PAGE_MEMBER,
            font_head=self._font_head,
            font_row=self._font_row,
            font_meta=self._font_meta,
        )

    def _render_spells(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        member = self._current_member()
        if member is None:
            return
        x = panel.x + 18
        y = panel.y + 52
        sub = self._font_meta.render(f"{member.name}'s spells", True, MUTED)
        screen.blit(sub, (panel.right - 18 - sub.get_width(), panel.y + 19))

        row_h = ROW_H + 8
        list_w = panel.w - 36
        sel = self._page(PAGE_SPELL).selection
        detail_h = 142
        visible_h = panel.bottom - y - detail_h - 18
        max_rows = max(1, visible_h // row_h)
        first = max(0, min(sel - max_rows + 1, max(0, len(self._spells) - max_rows)))

        for i, spell in enumerate(self._spells[first:first + max_rows], start=first):
            selected = (i == sel)
            castable = is_field_castable(spell)
            can_afford = member.mp >= spell["mp_cost"]
            if castable and can_afford:
                color = INK
            elif castable:
                color = MUTED
            else:
                color = DIM

            mp_cost = spell["mp_cost"]
            badge = "field cast" if castable else "battle only"
            rect = pygame.Rect(x, y + (i - first) * row_h, list_w, ROW_H)
            render_icon_row(
                screen,
                self._font_row,
                rect,
                spell["name"],
                icon_key=_spell_icon_key(spell),
                focused=selected,
                dimmed_sel=False,
                color=color,
                right_text=f"MP {mp_cost}",
                right_font=self._font_meta,
                subtext=f"{badge} / {spell.get('target', 'self')}",
                sub_font=self._font_small,
            )

        if self._spells:
            detail_y = panel.bottom - detail_h
            draw_divider(screen, x, detail_y - 12, list_w)
            self._render_spell_detail(screen, pygame.Rect(x, detail_y, list_w, detail_h), self._spells[sel], member)

    def _render_spell_detail(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        spell: dict,
        member: MemberState,
    ) -> None:
        castable = is_field_castable(spell)
        can_afford = member.mp >= spell["mp_cost"]
        color = TEAL if castable and can_afford else GOLD if castable else EMBER
        icon = _spell_icon_key(spell)
        render_icon_row(
            screen,
            self._font_row,
            pygame.Rect(rect.x, rect.y, min(360, rect.w), 54),
            spell["name"],
            icon_key=icon,
            focused=True,
            dimmed_sel=False,
            color=INK,
            right_text=f"MP {spell['mp_cost']}",
            right_font=self._font_meta,
            subtext=spell.get("type", "spell"),
            sub_font=self._font_small,
        )
        state_text = "Ready" if castable and can_afford else "Low MP" if castable else "Battle"
        state = self._font_meta.render(state_text, True, color)
        screen.blit(state, (rect.x + 380, rect.y + 17))

        desc = spell.get("description", "")
        if desc:
            y = rect.y + 66
            for line in wrap_text(self._font_meta, desc, rect.w - 10, limit=3):
                text = self._font_meta.render(line, True, MUTED)
                screen.blit(text, (rect.x, y))
                y += self._font_meta.get_height() + 3

    def _render_spellbook_idle(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        x = panel.x + 24
        y = panel.y + 64
        names = ("healing rites", "warding sigils", "travel charms", "battle arts")
        for i, name in enumerate(names):
            rect = pygame.Rect(x, y + i * 58, panel.w - 48, 46)
            render_icon_row(
                screen,
                self._font_meta,
                rect,
                name.title(),
                icon_key=f"idle_spell_{i}",
                focused=False,
                dimmed_sel=False,
                color=MUTED,
                right_text="sealed",
                right_font=self._font_small,
            )

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        if self.page_id == PAGE_MEMBER:
            text = "UP/DOWN select member    ENTER view spells    ESC close"
        else:
            text = "UP/DOWN select spell    ENTER cast    ESC back"
        hint = self._font_hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))


def _spell_icon_key(spell: dict) -> str:
    if spell.get("warp"):
        return "spell_warp"
    element = spell.get("element")
    if element:
        return f"spell_{element}"
    return f"spell_{spell.get('type', 'utility')}"
