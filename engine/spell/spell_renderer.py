# engine/spell/spell_renderer.py
#
# Drawing for the field Spells screen — caster column, spellbook list,
# spell detail, hints. SpellScene owns input/flow and the cast overlays;
# this class owns fonts and layout (follows the battle renderer split).

from __future__ import annotations

import pygame

from engine.common.color_constants import C_TEXT_DIM
from engine.common.font_provider import FontSet
from engine.common.font_roles import CAPTION
from engine.common.member_card import member_column_width, render_member_column
from engine.common.menu_popup import render_popup
from engine.common.ui.chrome import (
    draw_divider,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    wrap_text,
)
from engine.common.ui.theme import DIM, EMBER, GOLD, INK, MUTED, TEAL
from engine.party.member_state import MemberState
from engine.spell.spell_logic import is_field_castable

PAGE_MEMBER = "member"
PAGE_SPELL  = "spell"

PAD_X = 40
PAD_Y = 30
GAP = 18
ROW_H = 58


class SpellRenderer:
    def __init__(self) -> None:
        self._fonts = FontSet(
            title=(24, True), head=(18, True), row=18,
            meta=CAPTION, hint=14, small=CAPTION,
        )

    def render(
        self,
        screen: pygame.Surface,
        *,
        page_id: str,
        members: list[MemberState],
        member: MemberState | None,
        member_selection: int,
        spell_selection: int,
        spells: list[dict],
    ) -> None:
        render_backdrop(screen)
        render_header(screen, self._fonts.title, self._fonts.hint,
                      "SPELLS", "field magic and forbidden arts", PAD_X, PAD_Y)

        member_rect, spell_rect = self._layout(screen)
        render_panel(screen, member_rect, active=page_id == PAGE_MEMBER,
                     title="Casters", title_font=self._fonts.head)
        self._render_members(screen, member_rect, members, member_selection, page_id)
        render_panel(screen, spell_rect, active=page_id == PAGE_SPELL,
                     title="Spellbook", title_font=self._fonts.head)
        if page_id == PAGE_SPELL:
            self._render_spells(screen, spell_rect, member, spells, spell_selection)
        else:
            self._render_spellbook_idle(screen, spell_rect)

        self._render_hint(screen, page_id)

    def render_popup(self, screen: pygame.Surface, text: str) -> None:
        """Drawn last by the scene so it sits above any overlay."""
        render_popup(screen, self._fonts.row, self._fonts.meta, text)

    # ── Layout ────────────────────────────────────────────────

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        panel_h = max(360, sh - top - 62)
        member_w = member_column_width(sw)
        spell_w = sw - PAD_X * 2 - GAP - member_w
        member_rect = pygame.Rect(PAD_X, top, member_w, panel_h)
        spell_rect = pygame.Rect(member_rect.right + GAP, top, spell_w, panel_h)
        return member_rect, spell_rect

    def _render_members(
        self, screen: pygame.Surface, panel: pygame.Rect,
        members: list[MemberState], selection: int, page_id: str,
    ) -> None:
        render_member_column(
            screen, panel, members,
            selection=selection,
            active_page=page_id == PAGE_MEMBER,
            font_head=self._fonts.head,
            font_row=self._fonts.row,
            font_meta=self._fonts.meta,
        )

    def _render_spells(
        self, screen: pygame.Surface, panel: pygame.Rect,
        member: MemberState | None, spells: list[dict], sel: int,
    ) -> None:
        if member is None:
            return
        x = panel.x + 18
        y = panel.y + 52
        sub = self._fonts.meta.render(f"{member.name}'s spells", True, MUTED)
        screen.blit(sub, (panel.right - 18 - sub.get_width(), panel.y + 19))

        row_h = ROW_H + 8
        list_w = panel.w - 36
        detail_h = 142
        visible_h = panel.bottom - y - detail_h - 18
        max_rows = max(1, visible_h // row_h)
        first = max(0, min(sel - max_rows + 1, max(0, len(spells) - max_rows)))

        for i, spell in enumerate(spells[first:first + max_rows], start=first):
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
                self._fonts.row,
                rect,
                spell["name"],
                icon_key=_spell_icon_key(spell),
                focused=selected,
                dimmed_sel=False,
                color=color,
                right_text=f"MP {mp_cost}",
                right_font=self._fonts.meta,
                subtext=f"{badge} / {spell.get('target', 'self')}",
                sub_font=self._fonts.small,
            )

        if spells:
            detail_y = panel.bottom - detail_h
            draw_divider(screen, x, detail_y - 12, list_w)
            self._render_spell_detail(
                screen, pygame.Rect(x, detail_y, list_w, detail_h), spells[sel], member,
            )

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
            self._fonts.row,
            pygame.Rect(rect.x, rect.y, min(360, rect.w), 54),
            spell["name"],
            icon_key=icon,
            focused=True,
            dimmed_sel=False,
            color=INK,
            right_text=f"MP {spell['mp_cost']}",
            right_font=self._fonts.meta,
            subtext=spell.get("type", "spell"),
            sub_font=self._fonts.small,
        )
        state_text = "Ready" if castable and can_afford else "Low MP" if castable else "Battle"
        state = self._fonts.meta.render(state_text, True, color)
        screen.blit(state, (rect.x + 380, rect.y + 17))

        desc = spell.get("description", "")
        if desc:
            y = rect.y + 66
            for line in wrap_text(self._fonts.meta, desc, rect.w - 10, limit=3):
                text = self._fonts.meta.render(line, True, MUTED)
                screen.blit(text, (rect.x, y))
                y += self._fonts.meta.get_height() + 3

    def _render_spellbook_idle(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        x = panel.x + 24
        y = panel.y + 64
        names = ("healing rites", "warding sigils", "travel charms", "battle arts")
        for i, name in enumerate(names):
            rect = pygame.Rect(x, y + i * 58, panel.w - 48, 46)
            render_icon_row(
                screen,
                self._fonts.meta,
                rect,
                name.title(),
                icon_key=f"idle_spell_{i}",
                focused=False,
                dimmed_sel=False,
                color=MUTED,
                right_text="sealed",
                right_font=self._fonts.small,
            )

    def _render_hint(self, screen: pygame.Surface, page_id: str) -> None:
        sw, sh = screen.get_size()
        if page_id == PAGE_MEMBER:
            text = "UP/DOWN select member    ENTER view spells    ESC close"
        else:
            text = "UP/DOWN select spell    ENTER cast    ESC back"
        hint = self._fonts.hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))


def _spell_icon_key(spell: dict) -> str:
    if spell.get("warp"):
        return "spell_warp"
    element = spell.get("element")
    if element:
        return f"spell_{element}"
    return f"spell_{spell.get('type', 'utility')}"
