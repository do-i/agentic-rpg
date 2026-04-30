# engine/inn/inn_scene.py

from __future__ import annotations

from pathlib import Path

import pygame
from engine.common.font_provider import get_fonts

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.menu_sfx_mixin import MenuSfxMixin
from engine.world.sprite_sheet import SpriteSheet

# ── Colors ────────────────────────────────────────────────────
C_BG        = (18, 18, 35)
C_BORDER    = (160, 160, 100)
C_HEADER    = (220, 220, 180)
C_TEXT      = (238, 238, 238)
C_MUTED     = (130, 130, 140)
C_GP        = (200, 185, 100)
C_HP        = (80, 200, 100)
C_MP        = (80, 140, 220)
C_BAR_BG    = (40, 40, 60)
C_DIVIDER   = (50, 50, 70)
C_HINT      = (100, 100, 115)
C_WARN      = (220, 100, 80)
C_TOAST     = (100, 220, 130)

# ── Layout ────────────────────────────────────────────────────
MODAL_W     = 520
PAD         = 24
HEADER_H    = 48
SPRITE_SIZE = 96
ROW_H       = 44
BAR_H       = 8
FOOTER_H    = 36
POPUP_W     = 360


class InnScene(MenuSfxMixin, Scene):
    """
    Inn rest overlay.  States: confirm → toast (auto-close).
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        cost: int,
        sprite_path: Path,
        sfx_manager,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close
        self._cost          = cost
        self._sprite_path   = sprite_path
        self._sfx_manager   = sfx_manager

        self._state         = "confirm"   # confirm | no_gp | popup
        self._fonts_ready   = False
        self._sprite_loaded = False
        self._sprite_surf: pygame.Surface | None = None

    # ── Init ──────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title  = f.get(22, bold=True)
        self._font_row    = f.get(16)
        self._font_hint   = f.get(15)
        self._font_toast  = f.get(22, bold=True)
        self._fonts_ready = True

    def _init_sprite(self) -> None:
        self._sprite_surf = SpriteSheet.load_npc_face(self._sprite_path, SPRITE_SIZE)
        self._sprite_loaded = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "popup":
                if self.is_popup_dismiss_key(event.key):
                    self._on_close()
                return
            if self._state in ("confirm", "no_gp"):
                if event.key == pygame.K_ESCAPE:
                    self._play("cancel")
                    self._on_close()
                elif event.key == pygame.K_RETURN:
                    self._play("confirm")
                    self._try_rest()

    def _try_rest(self) -> None:
        state = self._holder.get()
        if state.repository.gp < self._cost:
            self._state = "no_gp"
            return
        state.repository.spend_gp(self._cost)
        for member in state.party.members:
            member.hp = member.hp_max
            member.mp = member.mp_max
            if hasattr(member, "status_effects"):
                member.status_effects = []
        self._state       = "popup"

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        if not self._sprite_loaded:
            self._init_sprite()

        state   = self._holder.get()
        members = state.party.members
        rows    = max(len(members), 1)
        body_h  = PAD + SPRITE_SIZE + PAD // 2 + rows * ROW_H + PAD
        mh      = HEADER_H + body_h + FOOTER_H

        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - mh) // 2

        # dim background
        overlay = pygame.Surface(
            (screen.get_width(), screen.get_height()), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        # modal box
        pygame.draw.rect(screen, C_BG,     (mx, my, MODAL_W, mh), border_radius=8)
        pygame.draw.rect(screen, C_BORDER, (mx, my, MODAL_W, mh), 2, border_radius=8)

        self._draw_header(screen, mx, my, state.repository.gp)
        self._draw_body(screen, mx, my + HEADER_H, members)
        self._draw_footer(screen, mx, my + mh - FOOTER_H, state.repository.gp)

        if self._state == "popup":
            self._draw_popup(screen)

    def _draw_header(self, screen: pygame.Surface, mx: int, my: int, gp: int) -> None:
        title = self._font_title.render("Inn", True, C_HEADER)
        screen.blit(title, (mx + PAD, my + (HEADER_H - title.get_height()) // 2))

        gp_s = self._font_row.render(f"GP  {gp:,}", True, C_GP)
        screen.blit(gp_s, (mx + MODAL_W - gp_s.get_width() - PAD,
                            my + (HEADER_H - gp_s.get_height()) // 2))

        pygame.draw.line(screen, C_DIVIDER,
                         (mx + 10, my + HEADER_H),
                         (mx + MODAL_W - 10, my + HEADER_H))

    def _draw_body(self, screen: pygame.Surface, mx: int, my: int, members) -> None:
        body_y = my + PAD

        # innkeeper sprite
        if self._sprite_surf:
            screen.blit(self._sprite_surf, (mx + PAD, body_y))

        # cost label beside sprite
        cost_s = self._font_title.render(f"{self._cost:,} GP / night", True, C_GP)
        screen.blit(cost_s, (mx + PAD + SPRITE_SIZE + PAD,
                              body_y + (SPRITE_SIZE - cost_s.get_height()) // 2))

        # party HP/MP rows
        row_y = body_y + SPRITE_SIZE + PAD // 2
        for member in members:
            self._draw_member_row(screen, mx + PAD, row_y, MODAL_W - PAD * 2, member)
            row_y += ROW_H

    def _draw_member_row(self, screen, x, y, w, member) -> None:
        name_s = self._font_row.render(member.name, True, C_TEXT)
        screen.blit(name_s, (x, y + 4))

        bar_x   = x + 110
        bar_w   = (w - 110) // 2 - 8
        bar_y   = y + 6
        bar_y2  = y + 6 + BAR_H + 6

        # HP bar
        hp_label = self._font_hint.render("HP", True, C_MUTED)
        screen.blit(hp_label, (bar_x, bar_y))
        bx = bar_x + 22
        pygame.draw.rect(screen, C_BAR_BG, (bx, bar_y, bar_w, BAR_H), border_radius=3)
        hp_ratio = member.hp / member.hp_max if member.hp_max else 0
        pygame.draw.rect(screen, C_HP,
                         (bx, bar_y, int(bar_w * hp_ratio), BAR_H), border_radius=3)
        hp_s = self._font_hint.render(f"{member.hp}/{member.hp_max}", True, C_MUTED)
        screen.blit(hp_s, (bx + bar_w + 4, bar_y))

        # MP bar
        mp_label = self._font_hint.render("MP", True, C_MUTED)
        screen.blit(mp_label, (bar_x, bar_y2))
        pygame.draw.rect(screen, C_BAR_BG, (bx, bar_y2, bar_w, BAR_H), border_radius=3)
        mp_ratio = member.mp / member.mp_max if member.mp_max else 0
        pygame.draw.rect(screen, C_MP,
                         (bx, bar_y2, int(bar_w * mp_ratio), BAR_H), border_radius=3)
        mp_s = self._font_hint.render(f"{member.mp}/{member.mp_max}", True, C_MUTED)
        screen.blit(mp_s, (bx + bar_w + 4, bar_y2))

    def _draw_footer(self, screen: pygame.Surface, mx: int, y: int, gp: int) -> None:
        pygame.draw.line(screen, C_DIVIDER,
                         (mx + 10, y),
                         (mx + MODAL_W - 10, y))

        if self._state == "no_gp":
            msg = self._font_hint.render("Not enough GP.", True, C_WARN)
            screen.blit(msg, (mx + PAD, y + (FOOTER_H - msg.get_height()) // 2))
        else:
            hint = self._font_hint.render(
                "ENTER  rest · ESC  cancel", True, C_HINT)
            screen.blit(hint, (mx + PAD, y + (FOOTER_H - hint.get_height()) // 2))

    def _draw_popup(self, screen: pygame.Surface) -> None:
        ph = 80
        px = (screen.get_width()  - POPUP_W) // 2
        py = (screen.get_height() - ph) // 2
        pygame.draw.rect(screen, C_BG,     (px, py, POPUP_W, ph), border_radius=6)
        pygame.draw.rect(screen, C_BORDER, (px, py, POPUP_W, ph), 2, border_radius=6)
        msg = self._font_toast.render("The party rested and recovered!", True, C_TOAST)
        screen.blit(msg, (px + (POPUP_W - msg.get_width()) // 2, py + 14))
        hint = self._font_hint.render("ENTER / ESC  close", True, C_HINT)
        screen.blit(hint, (px + (POPUP_W - hint.get_width()) // 2, py + ph - 28))
