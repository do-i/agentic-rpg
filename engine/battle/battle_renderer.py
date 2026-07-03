# engine/battle/battle_renderer.py
#
# Battle screen orchestrator. The top section (enemy area) is unchanged; the
# bottom section is restyled to match the field-menu UI: three themed panels —
# Party (left, 100px portrait cards laid out left-to-right), Command (middle),
# and Log (right). Asset loading lives in BattleAssetCache; the additive flash
# overlay and damage-float caches live inside the panel renderers that own them.

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
    CARD_GAP, CARD_PORTRAIT, INNER_PAD, PANEL_GAP, PANEL_MARGIN,
)
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H
from engine.common.color_constants import C_BG
from engine.common.font_provider import get_fonts
from engine.common.ui.theme import EMBER, TEAL
from engine.common.ui.chrome import render_panel, wrap_text


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
        self._screen_w = screen_width
        self._screen_h = screen_height
        self._fonts_ready = False

        # The enemy area and party panel share a HitFlash: the additive
        # overlay logic is the same on both halves of the screen.
        self._hit_flash = HitFlash()
        self._enemy_area = EnemyAreaRenderer(self._assets, screen_width, self._hit_flash)
        self._party_panel = PartyPanelRenderer(self._hit_flash)
        self._command_panel = CommandPanelRenderer()
        self._damage_floats = DamageFloatRenderer(self._assets)

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_head = f.get(18, bold=True)
        self._font_msg = f.get(18)
        self._fonts_ready = True

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
        if not self._fonts_ready:
            self._init_fonts()

        bg = self._assets.load_background(state.background) if state.background else None
        bottom_h = self._screen_h - ENEMY_AREA_H
        if bg is not None:
            screen.blit(bg, (0, 0), area=(0, 0, self._screen_w, ENEMY_AREA_H))
            screen.fill(C_BG, (0, ENEMY_AREA_H, self._screen_w, bottom_h))
        else:
            screen.fill(C_BG)

        self._enemy_area.draw(screen, state, target_pool, target_sel,
                              has_bg=bg is not None, fx=fx)

        party_rect, cmd_rect, msg_rect = self._layout(len(state.party))

        render_panel(screen, party_rect, active=False,
                     title="Party", title_font=self._font_head)
        self._party_panel.draw(screen, party_rect, state,
                               target_pool, target_sel, fx=fx)

        active = state.active
        cmd_title = f"{active.name}'s Turn" if active else "Command"
        render_panel(screen, cmd_rect, active=True,
                     title=cmd_title, title_font=self._font_head)
        self._command_panel.draw(screen, cmd_rect, state,
                                 cmd_items, cmd_sel, sub_items, sub_sel)

        render_panel(screen, msg_rect, active=False,
                     title="Log", title_font=self._font_head)
        self._draw_message(screen, msg_rect, resolve_msg, resolve_is_enemy)

        self._damage_floats.draw(screen, state)

    def _layout(self, member_count: int) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Compute the three bottom panels. Party widens to fit one 100px
        portrait column per member; Command and Log share what remains on the
        right, keeping a sensible minimum width even with a full 5-member party."""
        top = ENEMY_AREA_H + PANEL_MARGIN
        h = self._screen_h - ENEMY_AREA_H - PANEL_MARGIN * 2

        n = max(1, member_count)
        card_w = CARD_PORTRAIT + 8
        party_w = n * card_w + (n - 1) * CARD_GAP + INNER_PAD * 2
        party_w = min(party_w, self._screen_w - 460)   # reserve room for cmd + log

        party_rect = pygame.Rect(PANEL_MARGIN, top, party_w, h)
        right_x = party_rect.right + PANEL_GAP
        right_w = self._screen_w - PANEL_MARGIN - right_x
        cmd_w = max(220, int(right_w * 0.45))
        cmd_rect = pygame.Rect(right_x, top, cmd_w, h)
        msg_x = cmd_rect.right + PANEL_GAP
        msg_rect = pygame.Rect(msg_x, top, self._screen_w - PANEL_MARGIN - msg_x, h)
        return party_rect, cmd_rect, msg_rect

    def _draw_message(
        self, screen: pygame.Surface, panel: pygame.Rect,
        resolve_msg: str, is_enemy: bool,
    ) -> None:
        if not resolve_msg:
            return
        color = EMBER if is_enemy else TEAL
        x = panel.x + 16
        y = panel.y + 50
        w = panel.w - 32
        for line in wrap_text(self._font_msg, resolve_msg, w, limit=6):
            surf = self._font_msg.render(line, True, color)
            screen.blit(surf, (x, y))
            y += surf.get_height() + 4
