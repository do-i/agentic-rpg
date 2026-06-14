# engine/battle/battle_party_panel_renderer.py
#
# Draws the bottom-left party roster. Each member is a vertical card laid out
# left-to-right: a 100x100 framed portrait (identical to the field-menu /
# equipment screens) over the name and HP/MP bars. Styling comes from
# field_menu_theme so the bottom of the battle screen matches the menu UI.

from __future__ import annotations

import pygame

from engine.battle.battle_fx import BattleFx
from engine.battle.battle_hit_flash import HitFlash
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant
from engine.battle.battle_renderer_constants import (
    CARD_GAP, CARD_PORTRAIT, INNER_PAD, STATUS_COLORS,
    C_HP_BAR, C_HP_BAR_LOW, C_MP_BAR,
)
from engine.common.color_constants import HP_LOW_THRESHOLD
from engine.common.font_provider import get_fonts
from engine.common.field_menu_theme import (
    DIM, INK,
    draw_stat_bar, fit_text, icon_surface, member_icon_path, render_row_frame,
)

C_TARGET = (204, 170, 255)
CARD_PAD = 4   # horizontal breathing room either side of the 100px portrait
BAR_H    = 18


class PartyPanelRenderer:
    """Bottom-left party roster as left-to-right portrait cards."""

    def __init__(self, hit_flash: HitFlash) -> None:
        self._hit_flash = hit_flash
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_name  = f.get(18, bold=True)
        self._font_bar   = f.get(14)
        self._font_badge = f.get(11, bold=True)
        self._fonts_ready = True

    def draw(
        self,
        screen: pygame.Surface,
        panel: pygame.Rect,
        state: BattleState,
        target_pool: list[Combatant],
        target_sel: int,
        fx: BattleFx | None,
    ) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        members = state.party
        if not members:
            return

        content_x = panel.x + INNER_PAD
        content_top = panel.y + 44
        avail_h = (panel.bottom - 14) - content_top
        card_w = CARD_PORTRAIT + CARD_PAD * 2
        card_h = min(avail_h, 196)
        card_y = content_top + (avail_h - card_h) // 2

        for i, member in enumerate(members):
            card = pygame.Rect(
                content_x + i * (card_w + CARD_GAP), card_y, card_w, card_h,
            )
            self._draw_card(screen, card, member, state,
                            target_pool, target_sel, fx)

    def _draw_card(
        self, screen: pygame.Surface, card: pygame.Rect,
        member: Combatant, state: BattleState,
        target_pool: list[Combatant], target_sel: int,
        fx: BattleFx | None,
    ) -> None:
        active = state.active
        is_active = active is not None and active is member and not member.is_enemy
        is_target = (state.phase == BattlePhase.SELECT_TARGET
                     and target_pool
                     and target_sel < len(target_pool)
                     and target_pool[target_sel] is member)

        render_row_frame(screen, card, focused=is_active, dimmed_sel=False)
        if is_target:
            pygame.draw.rect(screen, C_TARGET, card.inflate(4, 4), 2, border_radius=6)

        # ── Portrait (100x100, framed exactly like the menu) ──────────
        px = card.x + CARD_PAD
        py = card.y + CARD_PAD + 2
        shake_dx = fx.shake_offset(member) if fx else 0
        ppx = px + shake_dx
        portrait = icon_surface(
            f"member_{member.id}", CARD_PORTRAIT,
            dimmed=member.is_ko, image_path=member_icon_path(member.id),
        )
        screen.blit(portrait, (ppx, py))
        self._hit_flash.apply(screen, member, ppx, py,
                              CARD_PORTRAIT, CARD_PORTRAIT, fx, sprite=portrait)
        if member.is_ko:
            ko = pygame.Surface((CARD_PORTRAIT, CARD_PORTRAIT), pygame.SRCALPHA)
            ko.fill((0, 0, 0, 150))
            screen.blit(ko, (px, py))

        self._draw_status_badge(screen, member, px, py)

        # ── Name ──────────────────────────────────────────────────────
        name_col = DIM if member.is_ko else INK
        name = fit_text(self._font_name, member.name, name_col, CARD_PORTRAIT)
        ny = py + CARD_PORTRAIT + 6
        screen.blit(name, (px + (CARD_PORTRAIT - name.get_width()) // 2, ny))

        # ── HP / MP bars ───────────────────────────────────────────────
        bar_y = ny + name.get_height() + 6
        hp_col = C_HP_BAR_LOW if member.hp_pct <= HP_LOW_THRESHOLD else C_HP_BAR
        self._draw_bar(screen, px, bar_y, "HP",
                       member.hp, member.hp_max, hp_col, member.is_ko)
        if member.mp_max > 0:
            self._draw_bar(screen, px, bar_y + BAR_H + 4, "MP",
                           member.mp, member.mp_max, C_MP_BAR, member.is_ko)

    def _draw_bar(
        self, screen: pygame.Surface, x: int, y: int, label: str,
        value: int, maximum: int, color: tuple[int, int, int], ko: bool,
    ) -> None:
        rect = pygame.Rect(x, y, CARD_PORTRAIT, BAR_H)
        draw_stat_bar(screen, rect, 0 if ko else value, maximum, color)
        lbl = self._font_bar.render(label, True, INK)
        screen.blit(lbl, (x + 5, y + (BAR_H - lbl.get_height()) // 2))
        val = self._font_bar.render(f"{value}/{maximum}", True, INK)
        screen.blit(val, (x + CARD_PORTRAIT - 5 - val.get_width(),
                          y + (BAR_H - val.get_height()) // 2))

    def _draw_status_badge(
        self, screen: pygame.Surface, member: Combatant, px: int, py: int,
    ) -> None:
        if not member.status_effects:
            return
        effect = member.status_effects[0].effect
        if effect not in STATUS_COLORS:
            return
        bg_col, text_col, label = STATUS_COLORS[effect]
        bs = self._font_badge.render(label, True, text_col)
        bx = px + CARD_PORTRAIT - bs.get_width() - 6
        by = py + 6
        pygame.draw.rect(screen, bg_col,
                         (bx - 4, by - 2, bs.get_width() + 8, bs.get_height() + 4),
                         border_radius=3)
        screen.blit(bs, (bx, by))
