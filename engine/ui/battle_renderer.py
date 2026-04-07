# engine/ui/battle_renderer.py
#
# Battle rendering — all drawing, fonts, portrait loading, layout.
# Extracted from battle_scene.py to separate rendering from game logic.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.battle.combatant import Combatant, StatusEffect
from engine.battle.battle_state import BattleState, BattlePhase
from engine.settings import Settings

# ── Layout ────────────────────────────────────────────────────
ENEMY_AREA_H    = int(Settings.SCREEN_HEIGHT * 0.65)
BOTTOM_H        = Settings.SCREEN_HEIGHT - ENEMY_AREA_H
PARTY_W         = Settings.SCREEN_WIDTH // 2
CMD_W           = Settings.SCREEN_WIDTH - PARTY_W

PORTRAIT_SIZE   = 36
ROW_H           = 44
ROW_PAD         = 8
BAR_H           = 6

STATUS_COLORS = {
    StatusEffect.POISON:  ((51, 102, 51),  (170, 255, 170), "PSN"),
    StatusEffect.SLEEP:   ((68, 68, 170),  (204, 204, 255), "zzz"),
    StatusEffect.STUN:    ((120, 90, 20),  (255, 220, 100), "STN"),
    StatusEffect.SILENCE: ((100, 60, 100), (220, 180, 220), "SIL"),
}

# ── Colors ────────────────────────────────────────────────────
C_BG           = (13,  13,  26)
C_FLOOR        = (17,  17,  40)
C_PANEL_LINE   = (51,  51,  51)
C_ROW_ACTIVE   = (42,  26,  26)
C_ROW_NORMAL   = (26,  26,  42)
C_BORDER_ACT   = (204, 68,  68)
C_BORDER_NORM  = (51,  51,  68)
C_CMD_SEL_BG   = (42,  32,  64)
C_CMD_SEL_BDR  = (119, 85,  204)
C_TEXT         = (238, 238, 238)
C_TEXT_MUT     = (170, 170, 170)
C_TEXT_DIM     = (102, 102, 102)
C_HP_OK        = (68,  170, 68)
C_HP_LOW       = (204, 68,  68)
C_MP           = (68,  102, 204)
C_HP_LABEL_OK  = (136, 204, 136)
C_HP_LABEL_LOW = (204, 136, 136)
C_MP_LABEL     = (136, 136, 204)

HP_LOW_THRESHOLD = 0.35

ENEMY_LAYOUTS = {
    1: [(0,   0)],
    2: [(-80, 0),  (80,  0)],
    3: [(-110, -30), (0, 20), (110, -20)],
    4: [(-140, -20), (-45, 20), (45, -20), (140, 20)],
    5: [(-160, -30), (-80, 20), (0, -10), (80, 20), (160, -30)],
}

ENEMY_SIZES = {
    "boss":   (96, 96),
    "large":  (80, 80),
    "medium": (64, 64),
    "small":  (52, 52),
}


class BattleRenderer:
    """Handles all rendering for the battle scene."""

    def __init__(self, scenario_path: Path) -> None:
        self._scenario_path = scenario_path
        self._fonts_ready = False
        self._portraits: dict[str, pygame.Surface] = {}
        self._enemy_size: dict[str, tuple] = {}

    def _init_fonts(self) -> None:
        self._font_name  = pygame.font.SysFont("Arial", 14, bold=True)
        self._font_stat  = pygame.font.SysFont("Arial", 12)
        self._font_cmd   = pygame.font.SysFont("Arial", 16)
        self._font_sub   = pygame.font.SysFont("Arial", 14)
        self._font_turn  = pygame.font.SysFont("Arial", 13)
        self._font_msg   = pygame.font.SysFont("Arial", 13)
        self._font_dmg   = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_enemy = pygame.font.SysFont("Arial", 11)
        self._font_badge = pygame.font.SysFont("Arial", 9,  bold=True)
        self._fonts_ready = True

    def _load_portrait(self, member_id: str) -> pygame.Surface | None:
        if member_id in self._portraits:
            return self._portraits[member_id]
        path = self._scenario_path / "assets" / "images" / f"{member_id}_profile.png"
        if not path.exists():
            return None
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            img = pygame.transform.scale(img, (PORTRAIT_SIZE, PORTRAIT_SIZE))
            self._portraits[member_id] = img
            return img
        except Exception:
            return None

    def _enemy_rect_size(self, enemy: Combatant) -> tuple:
        if enemy.id in self._enemy_size:
            return self._enemy_size[enemy.id]
        if enemy.boss:
            return ENEMY_SIZES["large"]
        idx = len(enemy.name) % 3
        return [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]

    # ── Main render ───────────────────────────────────────────

    def render(self, screen: pygame.Surface, state: BattleState,
               cmd_items: list[str], cmd_sel: int,
               sub_items: list[dict], sub_sel: int,
               target_pool: list[Combatant], target_sel: int,
               resolve_msg: str) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        screen.fill(C_BG)
        self._draw_enemy_area(screen, state, target_pool, target_sel)
        self._draw_action_message(screen, resolve_msg)
        self._draw_bottom_panel(screen, state, cmd_items, cmd_sel,
                                sub_items, sub_sel, target_pool, target_sel)
        self._draw_damage_floats(screen, state)

    def _draw_action_message(self, screen: pygame.Surface, resolve_msg: str) -> None:
        if not resolve_msg:
            return
        msg_h = 28
        msg_y = ENEMY_AREA_H - msg_h
        bg = pygame.Surface((Settings.SCREEN_WIDTH, msg_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        screen.blit(bg, (0, msg_y))
        text = self._font_cmd.render(resolve_msg, True, C_TEXT)
        screen.blit(text, (Settings.SCREEN_WIDTH // 2 - text.get_width() // 2, msg_y + 6))

    # ── Enemy area ────────────────────────────────────────────

    def _draw_enemy_area(self, screen: pygame.Surface, state: BattleState,
                         target_pool: list[Combatant], target_sel: int) -> None:
        pygame.draw.rect(screen, C_FLOOR,
                         (0, ENEMY_AREA_H - 60, Settings.SCREEN_WIDTH, 60))
        pygame.draw.line(screen, (42, 42, 68),
                         (0, ENEMY_AREA_H - 60), (Settings.SCREEN_WIDTH, ENEMY_AREA_H - 60))

        enemies = state.enemies
        n = len(enemies)
        offsets = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])
        cx = Settings.SCREEN_WIDTH // 2
        cy = ENEMY_AREA_H // 2 + 10

        for i, enemy in enumerate(enemies):
            ox, oy = offsets[i]
            self._draw_enemy(screen, enemy, cx + ox, cy + oy, i,
                             state, target_pool, target_sel)

    def _draw_enemy(self, screen: pygame.Surface, enemy: Combatant,
                    cx: int, cy: int, index: int,
                    state: BattleState,
                    target_pool: list[Combatant], target_sel: int) -> None:
        w, h = self._enemy_rect_size(enemy)
        rx, ry = cx - w // 2, cy - h // 2

        base_col = (30, 30, 40) if enemy.is_ko else (42, 58, 90)
        bdr_col  = (50, 50, 60) if enemy.is_ko else (74, 106, 154)
        pygame.draw.rect(screen, base_col, (rx, ry, w, h), border_radius=4)
        pygame.draw.rect(screen, bdr_col,  (rx, ry, w, h), 1, border_radius=4)

        name_surf = self._font_enemy.render(enemy.name, True, C_TEXT_MUT)
        screen.blit(name_surf, (cx - name_surf.get_width() // 2, ry + h + 4))

        bar_w = w
        bar_x = cx - bar_w // 2
        bar_y = ry + h + 4 + name_surf.get_height() + 3
        pygame.draw.rect(screen, (42, 42, 42), (bar_x, bar_y, bar_w, 5), border_radius=2)
        hp_fill = int(bar_w * enemy.hp_pct)
        hp_col  = C_HP_OK if enemy.hp_pct > HP_LOW_THRESHOLD else C_HP_LOW
        if hp_fill > 0 and not enemy.is_ko:
            pygame.draw.rect(screen, hp_col, (bar_x, bar_y, hp_fill, 5), border_radius=2)

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
                           target_pool: list[Combatant], target_sel: int) -> None:
        pygame.draw.line(screen, C_PANEL_LINE,
                         (0, ENEMY_AREA_H), (Settings.SCREEN_WIDTH, ENEMY_AREA_H))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (PARTY_W, ENEMY_AREA_H), (PARTY_W, Settings.SCREEN_HEIGHT))
        self._draw_party_panel(screen, state, target_pool, target_sel)
        self._draw_command_panel(screen, state, cmd_items, cmd_sel,
                                sub_items, sub_sel)

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

        rx, rw = ROW_PAD, PARTY_W - ROW_PAD * 2
        pygame.draw.rect(screen, bg,  (rx, y, rw, ROW_H - 2), border_radius=4)
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H - 2), 1, border_radius=4)
        if is_target:
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, y - 2, rw + 4, ROW_H + 2), 2, border_radius=5)

        px = rx + 6
        py = y + (ROW_H - 2 - PORTRAIT_SIZE) // 2
        img = self._load_portrait(member.id)
        if img:
            screen.blit(img, (px, py))
        else:
            col = (58, 42, 42) if is_active else (42, 42, 58)
            pygame.draw.rect(screen, col, (px, py, PORTRAIT_SIZE, PORTRAIT_SIZE), border_radius=3)
            init = "".join(w[0].upper() for w in member.name.split()[:2])
            s = self._font_badge.render(init, True, C_TEXT_MUT)
            screen.blit(s, (px + PORTRAIT_SIZE // 2 - s.get_width() // 2,
                             py + PORTRAIT_SIZE // 2 - s.get_height() // 2))

        if member.status_effects:
            effect = member.status_effects[0]
            if effect in STATUS_COLORS:
                bg_col, text_col, label = STATUS_COLORS[effect]
                bs = self._font_badge.render(label, True, text_col)
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
        bx = sx + 22
        bw = sw - 22 - 50

        screen.blit(self._font_name.render(
            member.name, True, C_TEXT if not member.is_ko else C_TEXT_DIM), (sx, y + 5))

        hp_pct  = member.hp_pct
        hp_col  = C_HP_LOW  if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
        hp_lcol = C_HP_LABEL_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_LABEL_OK
        screen.blit(self._font_stat.render("HP", True, hp_lcol), (sx, y + 20))
        pygame.draw.rect(screen, (42, 42, 42), (bx, y + 20, bw, BAR_H), border_radius=2)
        if not member.is_ko:
            pygame.draw.rect(screen, hp_col, (bx, y + 20, int(bw * hp_pct), BAR_H), border_radius=2)
        screen.blit(self._font_stat.render(f"{member.hp}/{member.hp_max}", True, hp_lcol),
                    (bx + bw + 4, y + 19))

        if member.mp_max > 0:
            mp_pct = member.mp / member.mp_max
            screen.blit(self._font_stat.render("MP", True, C_MP_LABEL), (sx, y + 32))
            pygame.draw.rect(screen, (42, 42, 42), (bx, y + 32, bw, BAR_H), border_radius=2)
            pygame.draw.rect(screen, C_MP, (bx, y + 32, int(bw * mp_pct), BAR_H), border_radius=2)
            screen.blit(self._font_stat.render(f"{member.mp}/{member.mp_max}", True, C_MP_LABEL),
                        (bx + bw + 4, y + 31))

    # ── Command panel ─────────────────────────────────────────

    def _draw_command_panel(self, screen: pygame.Surface, state: BattleState,
                           cmd_items: list[str], cmd_sel: int,
                           sub_items: list[dict], sub_sel: int) -> None:
        panel_x = PARTY_W + 20
        active  = state.active
        phase   = state.phase

        screen.blit(self._font_turn.render(
            f"{active.name}'s turn" if active else "", True, C_TEXT_MUT),
            (panel_x, ENEMY_AREA_H + 10))

        if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
            self._draw_submenu(screen, panel_x, ENEMY_AREA_H + 30,
                               sub_items, sub_sel)
        elif phase == BattlePhase.SELECT_TARGET:
            action = state.pending_action
            label = action.get("data", {}).get("name", "Attack") if action else "Attack"
            screen.blit(self._font_name.render(
                f"Select target for {label}", True, (204, 170, 255)),
                (panel_x, ENEMY_AREA_H + 34))
            screen.blit(self._font_stat.render(
                "\u2191\u2193 choose \u00b7 ENTER confirm \u00b7 ESC cancel", True, C_TEXT_MUT),
                (panel_x, ENEMY_AREA_H + 56))
        else:
            self._draw_main_cmd(screen, panel_x, ENEMY_AREA_H + 30, active,
                                cmd_items, cmd_sel)

    def _draw_main_cmd(self, screen: pygame.Surface,
                       x: int, y: int, active: Combatant | None,
                       cmd_items: list[str], cmd_sel: int) -> None:
        for i, label in enumerate(cmd_items):
            sel      = (i == cmd_sel)
            disabled = (label == "Spell" and active is not None and active.mp_max == 0)
            row_y    = y + i * 36

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 4, CMD_W - 30, 32), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 4, CMD_W - 30, 32), 1, border_radius=4)

            col = (C_TEXT_DIM if disabled
                   else (200, 160, 255) if sel else C_TEXT_MUT)

            if sel and not disabled:
                screen.blit(self._font_cmd.render("\u25b6", True, (200, 160, 255)), (x - 16, row_y))
            screen.blit(self._font_cmd.render(label, True, col), (x, row_y))

            if label == "Spell" and disabled:
                screen.blit(self._font_stat.render("\u2014", True, C_TEXT_DIM), (x + 60, row_y + 2))
            elif label in ("Item", "Spell") and not disabled:
                screen.blit(self._font_stat.render("\u2192", True, C_TEXT_DIM), (x + 60, row_y + 2))

    def _draw_submenu(self, screen: pygame.Surface, x: int, y: int,
                      sub_items: list[dict], sub_sel: int) -> None:
        for i, item in enumerate(sub_items):
            sel      = (i == sub_sel)
            disabled = item.get("disabled", False)
            row_y    = y + i * 28

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 3, CMD_W - 30, 26), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 3, CMD_W - 30, 26), 1, border_radius=4)

            col = C_TEXT_DIM if disabled else (C_TEXT if sel else C_TEXT_MUT)
            if sel and not disabled:
                screen.blit(self._font_sub.render("\u25b6", True, (200, 160, 255)), (x - 14, row_y))
            screen.blit(self._font_sub.render(item["label"], True, col), (x, row_y))

            if "mp_cost" in item:
                screen.blit(self._font_stat.render(
                    f"MP {item['mp_cost']}", True,
                    C_TEXT_DIM if disabled else C_MP_LABEL), (x + 160, row_y + 1))
            elif "qty" in item:
                screen.blit(self._font_stat.render(
                    f"\u00d7{item['qty']}", True, C_TEXT_MUT), (x + 160, row_y + 1))

        screen.blit(self._font_stat.render("ESC back", True, C_TEXT_DIM),
                    (x, y + len(sub_items) * 28 + 8))

    # ── Damage floats ─────────────────────────────────────────

    def _draw_damage_floats(self, screen: pygame.Surface, state: BattleState) -> None:
        for f in state.damage_floats:
            surf = self._font_dmg.render(f.text, True, f.color)
            surf.set_alpha(f.alpha)
            screen.blit(surf, (f.x, f.y))
