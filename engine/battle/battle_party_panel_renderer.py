# engine/battle/battle_party_panel_renderer.py
#
# Draws the bottom-left party roster: one row per party member with portrait,
# name, HP/MP bars, status badge, and KO scrim. Uses the same HitFlash helper
# as the enemy-area renderer.

from __future__ import annotations

import pygame

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_hit_flash import HitFlash
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H, ROW_H
from engine.battle.battle_renderer_constants import (
    BAR_H, PORTRAIT_SIZE, ROW_PAD, STATUS_COLORS,
    C_BORDER_ACT, C_BORDER_NORM,
    C_HP_LABEL_LOW, C_HP_LABEL_OK, C_HP_LOW, C_HP_OK,
    C_MP, C_MP_LABEL,
    C_ROW_ACTIVE, C_ROW_NORMAL,
)
from engine.common.color_constants import C_TEXT, C_TEXT_MUT, C_TEXT_DIM, HP_LOW_THRESHOLD


class PartyPanelRenderer:
    def __init__(
        self,
        assets: BattleAssetCache,
        party_w: int,
        hit_flash: HitFlash,
    ) -> None:
        self._assets = assets
        self._party_w = party_w
        self._hit_flash = hit_flash

    def draw(
        self,
        screen: pygame.Surface,
        state: BattleState,
        target_pool: list[Combatant],
        target_sel: int,
        fx: BattleFx | None,
    ) -> None:
        panel_y = ENEMY_AREA_H + 8
        for i, member in enumerate(state.party):
            self._draw_row(screen, member, panel_y + i * (ROW_H + 2),
                           state, target_pool, target_sel, fx=fx)

    def _draw_row(
        self, screen: pygame.Surface,
        member: Combatant, y: int,
        state: BattleState,
        target_pool: list[Combatant], target_sel: int,
        fx: BattleFx | None,
    ) -> None:
        active    = state.active
        is_active = active is not None and active is member and not member.is_enemy
        is_target = (state.phase == BattlePhase.SELECT_TARGET
                     and target_pool
                     and target_sel < len(target_pool)
                     and target_pool[target_sel] is member)
        bg  = C_ROW_ACTIVE if is_active else C_ROW_NORMAL
        bdr = C_BORDER_ACT if is_active else C_BORDER_NORM

        rx, rw = ROW_PAD, self._party_w - ROW_PAD * 2
        pygame.draw.rect(screen, bg,  (rx, y, rw, ROW_H - 2), border_radius=4)
        bdr_w = 2 if is_active else 1
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H - 2), bdr_w, border_radius=4)
        if is_target:
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, y - 2, rw + 4, ROW_H + 2), 2, border_radius=5)

        px = rx + 6
        py = y + (ROW_H - 2 - PORTRAIT_SIZE) // 2
        shake_dx = fx.shake_offset(member) if fx else 0
        ppx = px + shake_dx
        img = self._assets.load_portrait(member.id)
        if img:
            screen.blit(img, (ppx, py))
        else:
            col = (58, 42, 42) if is_active else (42, 42, 58)
            pygame.draw.rect(screen, col, (ppx, py, PORTRAIT_SIZE, PORTRAIT_SIZE), border_radius=3)
            init = "".join(w[0].upper() for w in member.name.split()[:2])
            s = self._assets.font_badge.render(init, True, C_TEXT_MUT)
            screen.blit(s, (ppx + PORTRAIT_SIZE // 2 - s.get_width() // 2,
                             py + PORTRAIT_SIZE // 2 - s.get_height() // 2))
        self._hit_flash.apply(screen, member, ppx, py,
                              PORTRAIT_SIZE, PORTRAIT_SIZE, fx, sprite=img)

        if member.status_effects:
            effect = member.status_effects[0].effect
            if effect in STATUS_COLORS:
                bg_col, text_col, label = STATUS_COLORS[effect]
                bs = self._assets.font_badge.render(label, True, text_col)
                bx = px + PORTRAIT_SIZE - bs.get_width() - 2
                pygame.draw.rect(screen, bg_col,
                                 (bx - 3, py - 7, bs.get_width() + 6, bs.get_height() + 2),
                                 border_radius=2)
                screen.blit(bs, (bx, py - 6))

        if member.is_ko:
            ko_surf = pygame.Surface((PORTRAIT_SIZE, PORTRAIT_SIZE), pygame.SRCALPHA)
            ko_surf.fill((0, 0, 0, 160))
            screen.blit(ko_surf, (px, py))

        sx = px + PORTRAIT_SIZE + 8
        sw = rw - PORTRAIT_SIZE - 20
        bar_h = BAR_H * 2 + 4
        bar_gap = 6
        bar_y = y + 22

        name_col = C_TEXT if not member.is_ko else C_TEXT_DIM
        screen.blit(self._assets.font_name.render(member.name, True, name_col), (sx, y + 4))

        hp_pct  = member.hp_pct
        hp_col  = C_HP_LOW  if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
        hp_lcol = C_HP_LABEL_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_LABEL_OK

        hp_label = self._assets.font_stat.render("HP", True, hp_lcol)
        hp_lw = hp_label.get_width()

        if member.mp_max > 0:
            mp_label = self._assets.font_stat.render("MP", True, C_MP_LABEL)
            mp_lw = mp_label.get_width()
            avail = sw - hp_lw - mp_lw - bar_gap * 3
            hp_bw = avail // 2
            mp_bw = avail - hp_bw
            hp_bx = sx + hp_lw + bar_gap
            mp_lx = hp_bx + hp_bw + bar_gap
            mp_bx = mp_lx + mp_lw + bar_gap
        else:
            hp_bw = sw - hp_lw - bar_gap
            hp_bx = sx + hp_lw + bar_gap
            mp_bw = 0
            mp_bx = 0

        screen.blit(hp_label, (sx, bar_y + bar_h // 2 - hp_label.get_height() // 2))
        pygame.draw.rect(screen, (42, 42, 42), (hp_bx, bar_y, hp_bw, bar_h), border_radius=3)
        if not member.is_ko:
            pygame.draw.rect(screen, hp_col, (hp_bx, bar_y, int(hp_bw * hp_pct), bar_h), border_radius=3)
        hp_txt = self._assets.font_stat.render(f"{member.hp}/{member.hp_max}", True, (255, 255, 255))
        screen.blit(hp_txt, (hp_bx + hp_bw // 2 - hp_txt.get_width() // 2,
                             bar_y + bar_h // 2 - hp_txt.get_height() // 2))

        if member.mp_max > 0:
            mp_pct = member.mp / member.mp_max
            screen.blit(mp_label, (mp_lx, bar_y + bar_h // 2 - mp_label.get_height() // 2))
            pygame.draw.rect(screen, (42, 42, 42), (mp_bx, bar_y, mp_bw, bar_h), border_radius=3)
            pygame.draw.rect(screen, C_MP, (mp_bx, bar_y, int(mp_bw * mp_pct), bar_h), border_radius=3)
            mp_txt = self._assets.font_stat.render(f"{member.mp}/{member.mp_max}", True, (255, 255, 255))
            screen.blit(mp_txt, (mp_bx + mp_bw // 2 - mp_txt.get_width() // 2,
                                 bar_y + bar_h // 2 - mp_txt.get_height() // 2))
