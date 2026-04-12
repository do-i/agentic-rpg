# engine/battle/battle_renderer.py
#
# Battle rendering — all drawing and layout.
# Fonts, portraits, and sprite loading are delegated to BattleAssetCache.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.battle.combatant import Combatant
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.constants import ENEMY_AREA_H, ENEMY_LAYOUTS, ROW_H
from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_renderer_constants import (
    BAR_H, PORTRAIT_SIZE, ROW_PAD, STATUS_COLORS,
    C_BORDER_ACT, C_BORDER_NORM, C_CMD_SEL_BDR, C_CMD_SEL_BG,
    C_FLOOR, C_HP_LABEL_LOW, C_HP_LABEL_OK, C_HP_LOW, C_HP_OK,
    C_MP, C_MP_LABEL, C_MSG_ENEMY, C_MSG_PARTY, C_PANEL_LINE,
    C_ROW_ACTIVE, C_ROW_NORMAL,
)
from engine.common.color_constants import C_BG, C_TEXT, C_TEXT_MUT, C_TEXT_DIM, HP_LOW_THRESHOLD


class BattleRenderer:
    """Handles all rendering for the battle scene."""

    def __init__(
        self,
        scenario_path: Path,
        screen_width: int = 1280,
        screen_height: int = 766,
    ) -> None:
        self._assets = BattleAssetCache(scenario_path)
        # ── Layout constants ──────────────────────────────────
        self._screen_w  = screen_width
        self._screen_h  = screen_height
        self.bottom_h   = screen_height - ENEMY_AREA_H
        self.party_w    = int(screen_width * 0.25)
        self.cmd_w      = int(screen_width * 0.30)
        self.msg_x      = self.party_w + self.cmd_w
        self.msg_w      = screen_width - self.msg_x

    # ── Main render ───────────────────────────────────────────

    def render(self, screen: pygame.Surface, state: BattleState,
               cmd_items: list[str], cmd_sel: int,
               sub_items: list[dict], sub_sel: int,
               target_pool: list[Combatant], target_sel: int,
               resolve_msg: str,
               resolve_is_enemy: bool = False) -> None:
        self._assets.init_fonts()

        bg = self._assets.load_background(state.background) if state.background else None
        if bg is not None:
            screen.blit(bg, (0, 0), area=(0, 0, self._screen_w, ENEMY_AREA_H))
            screen.fill(C_BG, (0, ENEMY_AREA_H, self._screen_w, self.bottom_h))
        else:
            screen.fill(C_BG)

        self._draw_enemy_area(screen, state, target_pool, target_sel, has_bg=bg is not None)
        self._draw_bottom_panel(screen, state, cmd_items, cmd_sel,
                                sub_items, sub_sel, target_pool, target_sel,
                                resolve_msg, resolve_is_enemy)
        self._draw_damage_floats(screen, state)

    def _draw_message_panel(self, screen: pygame.Surface, resolve_msg: str,
                            is_enemy: bool = False) -> None:
        if not resolve_msg:
            return
        color = C_MSG_ENEMY if is_enemy else C_MSG_PARTY
        text = self._assets.font_msg.render(resolve_msg, True, color)
        tx = self.msg_x + 10
        ty = ENEMY_AREA_H + 10
        screen.blit(text, (tx, ty))

    # ── Enemy area ────────────────────────────────────────────

    def _draw_enemy_area(self, screen: pygame.Surface, state: BattleState,
                         target_pool: list[Combatant], target_sel: int,
                         has_bg: bool = False) -> None:
        if not has_bg:
            pygame.draw.rect(screen, C_FLOOR,
                             (0, ENEMY_AREA_H - 60, self._screen_w, 60))
            pygame.draw.line(screen, (42, 42, 68),
                             (0, ENEMY_AREA_H - 60), (self._screen_w, ENEMY_AREA_H - 60))

        enemies = state.enemies
        n = len(enemies)
        offsets = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])
        cx = self._screen_w // 2
        cy = ENEMY_AREA_H // 2 + 10

        for i, enemy in enumerate(enemies):
            ox, oy = offsets[i]
            self._draw_enemy(screen, enemy, cx + ox, cy + oy, i,
                             state, target_pool, target_sel)

    def _draw_enemy(self, screen: pygame.Surface, enemy: Combatant,
                    cx: int, cy: int, index: int,
                    state: BattleState,
                    target_pool: list[Combatant], target_sel: int) -> None:
        w, h = self._assets.enemy_rect_size(enemy)
        rx, ry = cx - w // 2, cy - h // 2

        sprite = self._assets.load_enemy_sprite(enemy)
        if sprite is not None:
            img = sprite
            if enemy.is_ko:
                img = img.copy()
                img.set_alpha(80)
            screen.blit(img, (rx, ry))
        else:
            base_col = (30, 30, 40) if enemy.is_ko else (42, 58, 90)
            bdr_col  = (50, 50, 60) if enemy.is_ko else (74, 106, 154)
            pygame.draw.rect(screen, base_col, (rx, ry, w, h), border_radius=4)
            pygame.draw.rect(screen, bdr_col,  (rx, ry, w, h), 1, border_radius=4)

        bar_w = w
        bar_x = cx - bar_w // 2
        bar_y = ry + h + 4
        bar_h = 18
        # outer border – dark
        pygame.draw.rect(screen, (40, 40, 40), (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6), 2, border_radius=6)
        # inner border – light
        pygame.draw.rect(screen, (200, 200, 200), (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2), 2, border_radius=4)
        # bar background
        pygame.draw.rect(screen, (42, 42, 42), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        hp_fill = int(bar_w * enemy.hp_pct)
        hp_col  = C_HP_OK if enemy.hp_pct > HP_LOW_THRESHOLD else C_HP_LOW
        if hp_fill > 0 and not enemy.is_ko:
            pygame.draw.rect(screen, hp_col, (bar_x, bar_y, hp_fill, bar_h), border_radius=3)
        # name on the HP bar
        name_surf = self._assets.font_enemy.render(enemy.name, True, (255, 255, 255))
        name_x = bar_x + bar_w // 2 - name_surf.get_width() // 2
        name_y = bar_y + bar_h // 2 - name_surf.get_height() // 2
        # shadow for readability
        shadow = self._assets.font_enemy.render(enemy.name, True, (0, 0, 0))
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            screen.blit(shadow, (name_x + ox, name_y + oy))
        screen.blit(name_surf, (name_x, name_y))

        if (state.phase == BattlePhase.SELECT_TARGET
                and target_pool
                and index < len(target_pool)
                and target_pool[target_sel] is enemy):
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, ry - 2, w + 4, h + 4), 2, border_radius=5)

    # ── Bottom panel ──────────────────────────────────────────

    def _draw_bottom_panel(self, screen: pygame.Surface, state: BattleState,
                           cmd_items: list[str], cmd_sel: int,
                           sub_items: list[dict], sub_sel: int,
                           target_pool: list[Combatant], target_sel: int,
                           resolve_msg: str,
                           resolve_is_enemy: bool = False) -> None:
        pygame.draw.line(screen, C_PANEL_LINE,
                         (0, ENEMY_AREA_H), (self._screen_w, ENEMY_AREA_H))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (self.party_w, ENEMY_AREA_H), (self.party_w, self._screen_h))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (self.msg_x, ENEMY_AREA_H), (self.msg_x, self._screen_h))
        self._draw_party_panel(screen, state, target_pool, target_sel)
        self._draw_command_panel(screen, state, cmd_items, cmd_sel,
                                sub_items, sub_sel)
        self._draw_message_panel(screen, resolve_msg, resolve_is_enemy)

    def _draw_party_panel(self, screen: pygame.Surface, state: BattleState,
                          target_pool: list[Combatant], target_sel: int) -> None:
        panel_y = ENEMY_AREA_H + 8
        for i, member in enumerate(state.party):
            self._draw_party_row(screen, member, panel_y + i * (ROW_H + 2),
                                 state, target_pool, target_sel)

    def _draw_party_row(self, screen: pygame.Surface,
                        member: Combatant, y: int,
                        state: BattleState,
                        target_pool: list[Combatant], target_sel: int) -> None:
        active    = state.active
        is_active = active is not None and active is member and not member.is_enemy
        is_target = (state.phase == BattlePhase.SELECT_TARGET
                     and target_pool
                     and target_sel < len(target_pool)
                     and target_pool[target_sel] is member)
        bg  = C_ROW_ACTIVE if is_active else C_ROW_NORMAL
        bdr = C_BORDER_ACT if is_active else C_BORDER_NORM

        rx, rw = ROW_PAD, self.party_w - ROW_PAD * 2
        pygame.draw.rect(screen, bg,  (rx, y, rw, ROW_H - 2), border_radius=4)
        bdr_w = 2 if is_active else 1
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H - 2), bdr_w, border_radius=4)
        if is_target:
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, y - 2, rw + 4, ROW_H + 2), 2, border_radius=5)

        px = rx + 6
        py = y + (ROW_H - 2 - PORTRAIT_SIZE) // 2
        img = self._assets.load_portrait(member.id)
        if img:
            screen.blit(img, (px, py))
        else:
            col = (58, 42, 42) if is_active else (42, 42, 58)
            pygame.draw.rect(screen, col, (px, py, PORTRAIT_SIZE, PORTRAIT_SIZE), border_radius=3)
            init = "".join(w[0].upper() for w in member.name.split()[:2])
            s = self._assets.font_badge.render(init, True, C_TEXT_MUT)
            screen.blit(s, (px + PORTRAIT_SIZE // 2 - s.get_width() // 2,
                             py + PORTRAIT_SIZE // 2 - s.get_height() // 2))

        if member.status_effects:
            effect = member.status_effects[0]
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

        # ── Row 1: Name ──
        name_col = C_TEXT if not member.is_ko else C_TEXT_DIM
        screen.blit(self._assets.font_name.render(member.name, True, name_col), (sx, y + 4))

        hp_pct  = member.hp_pct
        hp_col  = C_HP_LOW  if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
        hp_lcol = C_HP_LABEL_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_LABEL_OK

        hp_label = self._assets.font_stat.render("HP", True, hp_lcol)
        hp_lw = hp_label.get_width()

        # ── Row 2: HP [bar]  <space>  MP [bar] ──
        if member.mp_max > 0:
            mp_label = self._assets.font_stat.render("MP", True, C_MP_LABEL)
            mp_lw = mp_label.get_width()
            # split remaining width after both labels and gaps
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

        # HP label + bar
        screen.blit(hp_label, (sx, bar_y + bar_h // 2 - hp_label.get_height() // 2))
        pygame.draw.rect(screen, (42, 42, 42), (hp_bx, bar_y, hp_bw, bar_h), border_radius=3)
        if not member.is_ko:
            pygame.draw.rect(screen, hp_col, (hp_bx, bar_y, int(hp_bw * hp_pct), bar_h), border_radius=3)
        hp_txt = self._assets.font_stat.render(f"{member.hp}/{member.hp_max}", True, (255, 255, 255))
        screen.blit(hp_txt, (hp_bx + hp_bw // 2 - hp_txt.get_width() // 2,
                             bar_y + bar_h // 2 - hp_txt.get_height() // 2))

        # MP label + bar
        if member.mp_max > 0:
            mp_pct = member.mp / member.mp_max
            screen.blit(mp_label, (mp_lx, bar_y + bar_h // 2 - mp_label.get_height() // 2))
            pygame.draw.rect(screen, (42, 42, 42), (mp_bx, bar_y, mp_bw, bar_h), border_radius=3)
            pygame.draw.rect(screen, C_MP, (mp_bx, bar_y, int(mp_bw * mp_pct), bar_h), border_radius=3)
            mp_txt = self._assets.font_stat.render(f"{member.mp}/{member.mp_max}", True, (255, 255, 255))
            screen.blit(mp_txt, (mp_bx + mp_bw // 2 - mp_txt.get_width() // 2,
                                 bar_y + bar_h // 2 - mp_txt.get_height() // 2))

    # ── Command panel ─────────────────────────────────────────

    def _draw_command_panel(self, screen: pygame.Surface, state: BattleState,
                           cmd_items: list[str], cmd_sel: int,
                           sub_items: list[dict], sub_sel: int) -> None:
        panel_x = self.party_w + 20
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
                "\u2191\u2193 choose \u00b7 ENTER confirm \u00b7 ESC cancel", True, C_TEXT_MUT),
                (panel_x, ENEMY_AREA_H + 56))
        else:
            show_sel = (phase == BattlePhase.PLAYER_TURN)
            self._draw_main_cmd(screen, panel_x, ENEMY_AREA_H + 30, active,
                                cmd_items, cmd_sel if show_sel else -1)

    def _draw_main_cmd(self, screen: pygame.Surface,
                       x: int, y: int, active: Combatant | None,
                       cmd_items: list[str], cmd_sel: int) -> None:
        for i, label in enumerate(cmd_items):
            sel      = (i == cmd_sel)
            disabled = (label == "Spell" and active is not None and active.mp_max == 0)
            row_y    = y + i * 36

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 4, self.cmd_w - 30, 32), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 4, self.cmd_w - 30, 32), 1, border_radius=4)

            col = (C_TEXT_DIM if disabled
                   else (200, 160, 255) if sel else C_TEXT_MUT)

            if sel and not disabled:
                screen.blit(self._assets.font_cmd.render("\u25b6", True, (200, 160, 255)), (x - 16, row_y))
            screen.blit(self._assets.font_cmd.render(label, True, col), (x, row_y))

            if label == "Spell" and disabled:
                screen.blit(self._assets.font_stat.render("\u2014", True, C_TEXT_DIM), (x + 60, row_y + 2))
            elif label in ("Item", "Spell") and not disabled:
                screen.blit(self._assets.font_stat.render("\u2192", True, C_TEXT_DIM), (x + 60, row_y + 2))

    def _draw_submenu(self, screen: pygame.Surface, x: int, y: int,
                      sub_items: list[dict], sub_sel: int) -> None:
        for i, item in enumerate(sub_items):
            sel      = (i == sub_sel)
            disabled = item.get("disabled", False)
            row_y    = y + i * 28

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 3, self.cmd_w - 30, 26), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 3, self.cmd_w - 30, 26), 1, border_radius=4)

            col = C_TEXT_DIM if disabled else (C_TEXT if sel else C_TEXT_MUT)
            if sel and not disabled:
                screen.blit(self._assets.font_sub.render("\u25b6", True, (200, 160, 255)), (x - 14, row_y))
            screen.blit(self._assets.font_sub.render(item["label"], True, col), (x, row_y))

            if "mp_cost" in item:
                screen.blit(self._assets.font_stat.render(
                    f"MP {item['mp_cost']}", True,
                    C_TEXT_DIM if disabled else C_MP_LABEL), (x + 160, row_y + 1))
            elif "qty" in item:
                screen.blit(self._assets.font_stat.render(
                    f"\u00d7{item['qty']}", True, C_TEXT_MUT), (x + 160, row_y + 1))

        screen.blit(self._assets.font_stat.render("ESC back", True, C_TEXT_DIM),
                    (x, y + len(sub_items) * 28 + 8))

    # ── Damage floats ─────────────────────────────────────────

    def _draw_damage_floats(self, screen: pygame.Surface, state: BattleState) -> None:
        for f in state.damage_floats:
            shadow = self._assets.font_dmg.render(f.text, True, (0, 0, 0))
            shadow.set_alpha(f.alpha)
            for ox, oy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2)):
                screen.blit(shadow, (f.x + ox, f.y + oy))
            surf = self._assets.font_dmg.render(f.text, True, f.color)
            surf.set_alpha(f.alpha)
            screen.blit(surf, (f.x, f.y))
