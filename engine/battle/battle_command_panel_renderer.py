# engine/battle/battle_command_panel_renderer.py
#
# Draws the bottom-middle command panel: the active combatant's main
# Attack/Defend/Spell/Item/Run list during PLAYER_TURN, the spell or item
# submenu during SELECT_SPELL/SELECT_ITEM, and the targeting prompt during
# SELECT_TARGET. Styled with field_menu_theme to match the menu UI.

from __future__ import annotations

import pygame

from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant
from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.field_menu_theme import (
    DIM, INK, MUTED, VIOLET, fit_text, render_row_frame,
)

C_TARGET = (204, 170, 255)


class CommandPanelRenderer:
    def __init__(self) -> None:
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_cmd  = f.get(20)
        self._font_sub  = f.get(18)
        self._font_meta = f.get(CAPTION)
        self._fonts_ready = True

    def draw(
        self,
        screen: pygame.Surface,
        panel: pygame.Rect,
        state: BattleState,
        cmd_items: list[str], cmd_sel: int,
        sub_items: list[dict], sub_sel: int,
    ) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        x = panel.x + 16
        y = panel.y + 50
        w = panel.w - 32
        phase = state.phase
        active = state.active

        if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
            self._draw_submenu(screen, x, y, w, sub_items, sub_sel)
        elif phase == BattlePhase.SELECT_TARGET:
            action = state.pending_action
            label = action.get("data", {}).get("name", "Attack") if action else "Attack"
            head = fit_text(self._font_sub, f"Select target for {label}", C_TARGET, w)
            screen.blit(head, (x, y))
            hint = self._font_meta.render(
                "choose · ENTER confirm · ESC cancel", True, MUTED)
            screen.blit(hint, (x, y + head.get_height() + 8))
        else:
            show_sel = (phase == BattlePhase.PLAYER_TURN)
            self._draw_main_cmd(screen, x, y, w, active,
                                cmd_items, cmd_sel if show_sel else -1)

    def _draw_main_cmd(
        self, screen: pygame.Surface, x: int, y: int, w: int,
        active: Combatant | None, cmd_items: list[str], cmd_sel: int,
    ) -> None:
        row_h = 36
        for i, label in enumerate(cmd_items):
            sel = (i == cmd_sel)
            disabled = (label == "Spell" and active is not None and active.mp_max == 0)
            rect = pygame.Rect(x, y + i * (row_h + 6), w, row_h)
            if sel and not disabled:
                render_row_frame(screen, rect, focused=True)
            color = DIM if disabled else (INK if sel else MUTED)
            txt = self._font_cmd.render(label, True, color)
            screen.blit(txt, (rect.x + 12, rect.y + (rect.h - txt.get_height()) // 2))
            if disabled:
                d = self._font_meta.render("no MP", True, DIM)
                screen.blit(d, (rect.right - 12 - d.get_width(),
                                rect.y + (rect.h - d.get_height()) // 2))

    def _draw_submenu(
        self, screen: pygame.Surface, x: int, y: int, w: int,
        sub_items: list[dict], sub_sel: int,
    ) -> None:
        row_h = 30
        for i, item in enumerate(sub_items):
            sel = (i == sub_sel)
            disabled = item.get("disabled", False)
            rect = pygame.Rect(x, y + i * (row_h + 4), w, row_h)
            if sel and not disabled:
                render_row_frame(screen, rect, focused=True)
            color = DIM if disabled else (INK if sel else MUTED)

            right = ""
            if "mp_cost" in item:
                right = f"MP {item['mp_cost']}"
            elif "qty" in item:
                right = f"x{item['qty']}"
            right_s = self._font_meta.render(
                right, True, DIM if disabled else MUTED) if right else None
            avail = w - 24 - (right_s.get_width() + 12 if right_s else 0)
            label = fit_text(self._font_sub, item["label"], color, avail)
            screen.blit(label, (rect.x + 12, rect.y + (rect.h - label.get_height()) // 2))
            if right_s:
                screen.blit(right_s, (rect.right - 12 - right_s.get_width(),
                                      rect.y + (rect.h - right_s.get_height()) // 2))

        hint = self._font_meta.render("ESC back", True, VIOLET)
        screen.blit(hint, (x, y + len(sub_items) * (row_h + 4) + 8))
