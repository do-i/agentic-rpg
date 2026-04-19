# engine/scenes/post_battle_scene.py
#
# Phase 4 — Battle system

from __future__ import annotations

import pygame
from engine.common.scene.scene import Scene
from engine.common.font_provider import get_fonts
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.battle.battle_rewards import BattleRewards, LevelUpResult
from engine.common.color_constants import C_BG, C_TEXT, C_TEXT_DIM as C_DIM, C_TEXT_MUT as C_MUTED

# ── Colors ────────────────────────────────────────────────────
C_HEADER      = (212, 200, 138)
C_EXP         = (106, 138, 238)
C_LEVELUP     = (255, 220,  80)
C_HP_GAIN     = (100, 220, 100)
C_MP_GAIN     = (100, 160, 255)
C_MC          = (180, 160, 100)
C_ITEM        = (160, 220, 160)
C_DIVIDER     = (51,  51,  68)
C_ROW_BG      = (26,  26,  46)
C_ROW_LVUP_BG = (40,  36,  10)
C_HINT        = (102, 102, 120)

PAD   = 32
ROW_H = 52


class PostBattleScene(Scene):
    """
    Displays EXP gained, level-ups, and loot after a victorious battle.
    Player presses SPACE / ENTER / Z to continue → world map.
    """

    def __init__(
        self,
        rewards: BattleRewards,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_continue: callable,
        sfx_manager=None,
    ) -> None:
        self._rewards = rewards
        self._scene_manager = scene_manager
        self._registry = registry
        self._on_continue = on_continue
        self._sfx_manager = sfx_manager
        self._fonts_ready = False

        # animate EXP bar filling
        self._exp_fill: float = 0.0      # 0.0 → 1.0
        self._exp_done: bool = False
        self._ready_to_exit: bool = False

    # ── Font init ─────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title  = f.get(22, bold=True)
        self._font_name   = f.get(16, bold=True)
        self._font_stat   = f.get(14)
        self._font_lvup   = f.get(15, bold=True)
        self._font_loot   = f.get(14)
        self._font_hint   = f.get(14)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                              pygame.K_KP_ENTER, pygame.K_z):
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                if not self._exp_done:
                    # skip animation
                    self._exp_fill = 1.0
                    self._exp_done = True
                    self._ready_to_exit = True
                elif self._ready_to_exit:
                    self._on_continue()

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if not self._exp_done:
            self._exp_fill = min(1.0, self._exp_fill + delta * 0.6)
            if self._exp_fill >= 1.0:
                self._exp_done = True
                self._ready_to_exit = True

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(C_BG)
        cx = screen.get_width() // 2
        y = PAD

        # ── Header ───────────────────────────────────────────
        title = self._font_title.render("Victory!", True, C_LEVELUP)
        screen.blit(title, (cx - title.get_width() // 2, y))
        y += title.get_height() + 8

        exp_s = self._font_stat.render(
            f"EXP gained:  {self._rewards.total_exp}", True, C_EXP)
        screen.blit(exp_s, (cx - exp_s.get_width() // 2, y))
        y += exp_s.get_height() + 16

        pygame.draw.line(screen, C_DIVIDER, (PAD, y), (screen.get_width() - PAD, y))
        y += 12

        # ── Member rows ───────────────────────────────────────
        for result in self._rewards.member_results:
            has_lvup = bool(result.level_ups)
            row_bg = C_ROW_LVUP_BG if has_lvup else C_ROW_BG
            pygame.draw.rect(screen, row_bg,
                             (PAD, y, screen.get_width() - PAD * 2, ROW_H),
                             border_radius=4)

            # name
            ko_tag = "  [KO]" if result.exp_gained == 0 else ""
            name_col = C_DIM if result.exp_gained == 0 else C_TEXT
            ns = self._font_name.render(result.member_name + ko_tag, True, name_col)
            screen.blit(ns, (PAD + 12, y + 8))

            # EXP share
            exp_col = C_DIM if result.exp_gained == 0 else C_EXP
            es = self._font_stat.render(
                f"+{result.exp_gained} EXP" if result.exp_gained else "-",
                True, exp_col)
            screen.blit(es, (PAD + 220, y + 10))

            # level-up badge
            if has_lvup:
                lu = result.level_ups[-1]
                lv_s = self._font_lvup.render(
                    f"LEVEL UP!  {lu.old_level}  {lu.new_level}", True, C_LEVELUP)
                screen.blit(lv_s, (PAD + 360, y + 6))

                gain_s = self._font_stat.render(
                    f"HP +{lu.hp_gained}   MP +{lu.mp_gained}", True, C_HP_GAIN)
                screen.blit(gain_s, (PAD + 360, y + 28))

            y += ROW_H + 4

        y += 8
        pygame.draw.line(screen, C_DIVIDER, (PAD, y), (screen.get_width() - PAD, y))
        y += 14

        # ── Loot ─────────────────────────────────────────────
        loot = self._rewards.loot
        loot_title = self._font_name.render("Loot", True, C_HEADER)
        screen.blit(loot_title, (PAD + 12, y))
        y += loot_title.get_height() + 8

        if loot.mc_drops:
            for mc in loot.mc_drops:
                mc_s = self._font_loot.render(
                    f"  Magic Core ({mc['size']})  x{mc['qty']}", True, C_MC)
                screen.blit(mc_s, (PAD + 12, y))
                y += mc_s.get_height() + 4

        if loot.item_drops:
            for item in loot.item_drops:
                it_s = self._font_loot.render(
                    f"  {item['name']}  x{item.get('qty', 1)}", True, C_ITEM)
                screen.blit(it_s, (PAD + 12, y))
                y += it_s.get_height() + 4

        if not loot.mc_drops and not loot.item_drops:
            none_s = self._font_loot.render("  -", True, C_DIM)
            screen.blit(none_s, (PAD + 12, y))

        # ── Continue hint ─────────────────────────────────────
        if self._ready_to_exit:
            hint = self._font_hint.render(
                "SPACE / ENTER  to continue", True, C_HINT)
            hx = cx - hint.get_width() // 2
            hy = screen.get_height() - PAD - hint.get_height()
            # subtle pulse using tick
            alpha = 128 + int(127 * abs(
                (pygame.time.get_ticks() % 1000) / 500.0 - 1.0))
            hint.set_alpha(alpha)
            screen.blit(hint, (hx, hy))
