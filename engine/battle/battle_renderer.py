# engine/battle/battle_renderer.py
#
# Battle screen orchestrator. Composes the four panel renderers (enemy area,
# party panel, command panel, damage floats) plus the inline message line
# and the background blit. Asset loading lives in BattleAssetCache; the
# additive flash overlay and KO-ghost / damage-float caches live inside
# the panel renderers that own them.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_command_panel_renderer import CommandPanelRenderer
from engine.battle.battle_damage_float_renderer import DamageFloatRenderer
from engine.battle.battle_enemy_area_renderer import EnemyAreaRenderer
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_hit_flash import HitFlash
from engine.battle.battle_party_panel_renderer import PartyPanelRenderer
from engine.battle.battle_renderer_constants import (
    C_MSG_ENEMY, C_MSG_PARTY, C_PANEL_LINE,
)
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H
from engine.common.color_constants import C_BG


class BattleRenderer:
    """Top-level battle renderer. Each frame it paints the background then
    delegates to one panel renderer per region of the screen."""

    def __init__(
        self,
        scenario_path: Path,
        screen_width: int = 1280,
        screen_height: int = 766,
    ) -> None:
        self._assets = BattleAssetCache(scenario_path)
        # ── Layout constants ──────────────────────────────────
        self._screen_w = screen_width
        self._screen_h = screen_height
        self.bottom_h  = screen_height - ENEMY_AREA_H
        self.party_w   = int(screen_width * 0.25)
        self.cmd_w     = int(screen_width * 0.30)
        self.msg_x     = self.party_w + self.cmd_w
        self.msg_w     = screen_width - self.msg_x

        # ── Panel renderers ───────────────────────────────────
        # The enemy area and party panel share a HitFlash: the additive
        # overlay logic is the same on both halves of the screen.
        self._hit_flash = HitFlash()
        self._enemy_area = EnemyAreaRenderer(self._assets, screen_width, self._hit_flash)
        self._party_panel = PartyPanelRenderer(self._assets, self.party_w, self._hit_flash)
        self._command_panel = CommandPanelRenderer(self._assets, self.party_w, self.cmd_w)
        self._damage_floats = DamageFloatRenderer(self._assets)

    def render(
        self,
        screen: pygame.Surface,
        state: BattleState,
        cmd_items: list[str], cmd_sel: int,
        sub_items: list[dict], sub_sel: int,
        target_pool: list[Combatant], target_sel: int,
        resolve_msg: str,
        resolve_is_enemy: bool = False,
        fx: BattleFx | None = None,
    ) -> None:
        self._assets.init_fonts()

        bg = self._assets.load_background(state.background) if state.background else None
        if bg is not None:
            screen.blit(bg, (0, 0), area=(0, 0, self._screen_w, ENEMY_AREA_H))
            screen.fill(C_BG, (0, ENEMY_AREA_H, self._screen_w, self.bottom_h))
        else:
            screen.fill(C_BG)

        self._enemy_area.draw(screen, state, target_pool, target_sel,
                              has_bg=bg is not None, fx=fx)
        self._draw_panel_dividers(screen)
        self._party_panel.draw(screen, state, target_pool, target_sel, fx=fx)
        self._command_panel.draw(screen, state, cmd_items, cmd_sel,
                                 sub_items, sub_sel)
        self._draw_message(screen, resolve_msg, resolve_is_enemy)
        self._damage_floats.draw(screen, state)

    def _draw_panel_dividers(self, screen: pygame.Surface) -> None:
        pygame.draw.line(screen, C_PANEL_LINE,
                         (0, ENEMY_AREA_H), (self._screen_w, ENEMY_AREA_H))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (self.party_w, ENEMY_AREA_H), (self.party_w, self._screen_h))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (self.msg_x, ENEMY_AREA_H), (self.msg_x, self._screen_h))

    def _draw_message(
        self, screen: pygame.Surface, resolve_msg: str, is_enemy: bool,
    ) -> None:
        if not resolve_msg:
            return
        color = C_MSG_ENEMY if is_enemy else C_MSG_PARTY
        text = self._assets.font_msg.render(resolve_msg, True, color)
        screen.blit(text, (self.msg_x + 10, ENEMY_AREA_H + 10))
