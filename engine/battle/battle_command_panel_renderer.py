# engine/battle/battle_command_panel_renderer.py
#
# Draws the bottom-middle command panel: the active combatant's turn header,
# the main Attack/Defend/Spell/Item/Run list during PLAYER_TURN, the spell
# or item submenu during SELECT_SPELL/SELECT_ITEM, and the targeting prompt
# during SELECT_TARGET.

from __future__ import annotations

import pygame

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H
from engine.battle.battle_renderer_constants import (
    C_CMD_SEL_BDR, C_CMD_SEL_BG, C_MP_LABEL,
)
from engine.common.color_constants import C_TEXT, C_TEXT_MUT, C_TEXT_DIM


class CommandPanelRenderer:
    def __init__(
        self,
        assets: BattleAssetCache,
        party_w: int,
        cmd_w: int,
    ) -> None:
        self._assets = assets
        self._party_w = party_w
        self._cmd_w = cmd_w

    def draw(
        self,
        screen: pygame.Surface,
        state: BattleState,
        cmd_items: list[str], cmd_sel: int,
        sub_items: list[dict], sub_sel: int,
    ) -> None:
        panel_x = self._party_w + 20
        active  = state.active
        phase   = state.phase

        screen.blit(self._assets.font_turn.render(
            f"{active.name}'s turn" if active else "", True, C_TEXT_MUT),
            (panel_x, ENEMY_AREA_H + 10))

        if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
            self._draw_submenu(screen, panel_x, ENEMY_AREA_H + 30,
                               sub_items, sub_sel)
        elif phase == BattlePhase.SELECT_TARGET:
            action = state.pending_action
            label = action.get("data", {}).get("name", "Attack") if action else "Attack"
            screen.blit(self._assets.font_name.render(
                f"Select target for {label}", True, (204, 170, 255)),
                (panel_x, ENEMY_AREA_H + 34))
            screen.blit(self._assets.font_stat.render(
                "choose · ENTER confirm · ESC cancel", True, C_TEXT_MUT),
                (panel_x, ENEMY_AREA_H + 56))
        else:
            show_sel = (phase == BattlePhase.PLAYER_TURN)
            self._draw_main_cmd(screen, panel_x, ENEMY_AREA_H + 30, active,
                                cmd_items, cmd_sel if show_sel else -1)

    def _draw_main_cmd(
        self, screen: pygame.Surface,
        x: int, y: int, active: Combatant | None,
        cmd_items: list[str], cmd_sel: int,
    ) -> None:
        for i, label in enumerate(cmd_items):
            sel      = (i == cmd_sel)
            disabled = (label == "Spell" and active is not None and active.mp_max == 0)
            row_y    = y + i * 36

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 4, self._cmd_w - 30, 32), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 4, self._cmd_w - 30, 32), 1, border_radius=4)

            col = (C_TEXT_DIM if disabled
                   else (200, 160, 255) if sel else C_TEXT_MUT)

            if sel and not disabled:
                screen.blit(self._assets.font_cmd.render(" ", True, (200, 160, 255)), (x - 16, row_y))
            screen.blit(self._assets.font_cmd.render(label, True, col), (x, row_y))

            if label == "Spell" and disabled:
                screen.blit(self._assets.font_stat.render("-", True, C_TEXT_DIM), (x + 60, row_y + 2))
            elif label in ("Item", "Spell") and not disabled:
                screen.blit(self._assets.font_stat.render(" ", True, C_TEXT_DIM), (x + 60, row_y + 2))

    def _draw_submenu(
        self, screen: pygame.Surface, x: int, y: int,
        sub_items: list[dict], sub_sel: int,
    ) -> None:
        for i, item in enumerate(sub_items):
            sel      = (i == sub_sel)
            disabled = item.get("disabled", False)
            row_y    = y + i * 28

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 3, self._cmd_w - 30, 26), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 3, self._cmd_w - 30, 26), 1, border_radius=4)

            col = C_TEXT_DIM if disabled else (C_TEXT if sel else C_TEXT_MUT)
            if sel and not disabled:
                screen.blit(self._assets.font_sub.render(" ", True, (200, 160, 255)), (x - 14, row_y))
            screen.blit(self._assets.font_sub.render(item["label"], True, col), (x, row_y))

            if "mp_cost" in item:
                screen.blit(self._assets.font_stat.render(
                    f"MP {item['mp_cost']}", True,
                    C_TEXT_DIM if disabled else C_MP_LABEL), (x + 160, row_y + 1))
            elif "qty" in item:
                screen.blit(self._assets.font_stat.render(
                    f"x{item['qty']}", True, C_TEXT_MUT), (x + 160, row_y + 1))

        screen.blit(self._assets.font_stat.render("ESC back", True, C_TEXT_DIM),
                    (x, y + len(sub_items) * 28 + 8))
