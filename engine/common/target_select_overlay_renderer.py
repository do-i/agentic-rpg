# engine/common/target_select_overlay_renderer.py
#
# Phase 6 — Shop + Apothecary

from __future__ import annotations

import pygame
from engine.party.member_state import MemberState

# ── Colors ────────────────────────────────────────────────────
C_BG          = (20, 20, 42)
C_BORDER      = (160, 140, 220)
C_HEADER      = (212, 200, 138)
C_SEL_BG      = (45, 42, 80)
C_SEL_BDR     = (180, 160, 255)
C_NORM_BDR    = (55, 55, 78)
C_ROW_BG      = (28, 28, 52)
C_TEXT        = (238, 238, 238)
C_MUTED       = (130, 130, 145)
C_DIM         = (75, 75, 85)
C_KO          = (100, 60, 60)
C_HP_OK       = (80, 180, 80)
C_HP_LOW      = (200, 70, 70)
C_MP          = (80, 110, 210)
C_WARN_BG     = (40, 30, 15)
C_WARN_BDR    = (200, 160, 60)
C_WARN_TXT    = (230, 200, 100)
C_HINT        = (100, 100, 118)

HP_LOW_THRESHOLD = 0.35

# ── Layout ────────────────────────────────────────────────────
MODAL_W    = 640
ROW_H      = 56
ROW_GAP    = 4
PAD        = 20
HEADER_H   = 44
FOOTER_H   = 30
BAR_W      = 90
BAR_H      = 7
WARN_H     = 36


class TargetSelectOverlay:
    """
    Reusable party target picker rendered as an overlay.
    Caller supplies a filtered list of valid targets.

    Usage:
        overlay = TargetSelectOverlay(
            targets=handler.valid_targets(item_id, party),
            item_label="Potion",
            on_confirm=lambda member: ...,
            on_cancel=lambda: ...,
        )
        # each frame: overlay.handle_events(events)
        #             overlay.render(screen)

    warning: if non-empty, shown as a yellow bar above the confirm hint.
             Set after apply() returns a warn-and-allow message.
    """

    def __init__(
        self,
        targets: list[MemberState],
        item_label: str,
        on_confirm: callable,
        on_cancel: callable,
        warning: str = "",
        sfx_manager=None,
    ) -> None:
        self._targets    = targets
        self._item_label = item_label
        self._on_confirm = on_confirm
        self._on_cancel  = on_cancel
        self.warning     = warning   # mutable — caller sets after apply()
        self._sfx_manager = sfx_manager

        self._sel        = 0
        self._fonts_ready = False

    # ── Font init ─────────────────────────────────────────────

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_name   = pygame.font.SysFont("Arial", 16, bold=True)
        self._font_arrow  = pygame.font.SysFont("Arial", 16)
        self._font_class  = pygame.font.SysFont("Arial", 13)
        self._font_stat   = pygame.font.SysFont("Arial", 13)
        self._font_hint   = pygame.font.SysFont("Arial", 14)
        self._font_warn   = pygame.font.SysFont("Arial", 14, bold=True)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                old = self._sel
                self._sel = (self._sel - 1) % max(len(self._targets), 1)
                if self._sel != old and self._sfx_manager:
                    self._sfx_manager.play("hover")
            elif event.key == pygame.K_DOWN:
                old = self._sel
                self._sel = (self._sel + 1) % max(len(self._targets), 1)
                if self._sel != old and self._sfx_manager:
                    self._sfx_manager.play("hover")
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._targets:
                    if self._sfx_manager:
                        self._sfx_manager.play("confirm")
                    self._on_confirm(self._targets[self._sel])
            elif event.key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_cancel()

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        rows   = max(len(self._targets), 1)
        warn_h = WARN_H if self.warning else 0
        body_h = rows * (ROW_H + ROW_GAP) + 8
        mh     = HEADER_H + body_h + warn_h + FOOTER_H + PAD * 2

        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - mh)      // 2

        # dim background
        dim = pygame.Surface(
            (screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # modal box
        pygame.draw.rect(screen, C_BG,     (mx, my, MODAL_W, mh), border_radius=8)
        pygame.draw.rect(screen, C_BORDER, (mx, my, MODAL_W, mh), 1, border_radius=8)

        self._draw_header(screen, mx, my)
        row_y = my + HEADER_H + PAD // 2
        if not self._targets:
            self._draw_empty(screen, mx, row_y)
        else:
            for i, member in enumerate(self._targets):
                self._draw_row(screen, member, mx, row_y, selected=(i == self._sel))
                row_y += ROW_H + ROW_GAP

        footer_y = my + mh - FOOTER_H - PAD // 2
        if self.warning:
            self._draw_warning(screen, mx, footer_y - WARN_H - 4)
        self._draw_footer(screen, mx, footer_y)

    def _draw_header(self, screen: pygame.Surface, mx: int, my: int) -> None:
        title = self._font_title.render(
            f"Use  {self._item_label}  —  Select Target", True, C_HEADER)
        screen.blit(title, (mx + PAD, my + (HEADER_H - title.get_height()) // 2))
        pygame.draw.line(screen, (55, 55, 78),
                         (mx + 8, my + HEADER_H),
                         (mx + MODAL_W - 8, my + HEADER_H))

    def _draw_empty(self, screen: pygame.Surface, mx: int, y: int) -> None:
        s = self._font_hint.render("No valid targets.", True, C_DIM)
        screen.blit(s, (mx + PAD, y + 12))

    def _draw_row(self, screen: pygame.Surface,
                  member: MemberState, mx: int, y: int, selected: bool) -> None:
        is_ko  = member.hp <= 0
        rx, rw = mx + 8, MODAL_W - 16

        bg  = C_SEL_BG  if selected else (C_KO if is_ko else C_ROW_BG)
        bdr = C_SEL_BDR if selected else C_NORM_BDR
        pygame.draw.rect(screen, bg,  (rx, y, rw, ROW_H), border_radius=4)
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H), 1, border_radius=4)

        if selected:
            cur = self._font_arrow.render("▶", True, C_HEADER)
            screen.blit(cur, (rx + 8, y + (ROW_H - cur.get_height()) // 2))

        # name + class
        tx = rx + 28
        name_col = C_TEXT if not is_ko else C_DIM
        screen.blit(self._font_name.render(member.name, True, name_col), (tx, y + 6))
        screen.blit(self._font_class.render(member.class_name, True, C_MUTED),
                    (tx, y + ROW_H - self._font_class.get_height() - 8))

        if is_ko:
            ko_s = self._font_name.render("[KO]", True, C_KO)
            screen.blit(ko_s, (tx + 120, y + (ROW_H - ko_s.get_height()) // 2))
            return

        # HP bar + value
        bx = rx + 200
        self._draw_bar_row(screen, "HP", member.hp, member.hp_max,
                           bx, y + 10, C_HP_LOW if member.hp / member.hp_max < HP_LOW_THRESHOLD else C_HP_OK)

        # MP bar + value (only if member has MP)
        if member.mp_max > 0:
            self._draw_bar_row(screen, "MP", member.mp, member.mp_max,
                               bx, y + 32, C_MP)
        else:
            no_mp = self._font_stat.render("MP  —", True, C_DIM)
            screen.blit(no_mp, (bx, y + 32))

    def _draw_bar_row(self, screen: pygame.Surface,
                      label: str, current: int, maximum: int,
                      x: int, y: int, bar_col: tuple) -> None:
        lbl = self._font_stat.render(label, True, C_MUTED)
        screen.blit(lbl, (x, y))
        bx = x + 28
        pygame.draw.rect(screen, (30, 30, 50), (bx, y + 3, BAR_W, BAR_H), border_radius=3)
        fill = int(BAR_W * min(current / maximum, 1.0)) if maximum > 0 else 0
        if fill > 0:
            pygame.draw.rect(screen, bar_col, (bx, y + 3, fill, BAR_H), border_radius=3)
        val = self._font_stat.render(f"{current}/{maximum}", True, C_MUTED)
        screen.blit(val, (bx + BAR_W + 8, y))

    def _draw_warning(self, screen: pygame.Surface, mx: int, y: int) -> None:
        pygame.draw.rect(screen, C_WARN_BG,  (mx + 8, y, MODAL_W - 16, WARN_H), border_radius=4)
        pygame.draw.rect(screen, C_WARN_BDR, (mx + 8, y, MODAL_W - 16, WARN_H), 1, border_radius=4)
        w = self._font_warn.render(f"⚠  {self.warning}", True, C_WARN_TXT)
        screen.blit(w, (mx + 20, y + (WARN_H - w.get_height()) // 2))

    def _draw_footer(self, screen: pygame.Surface, mx: int, y: int) -> None:
        pygame.draw.line(screen, (55, 55, 78),
                         (mx + 8, y), (mx + MODAL_W - 8, y))
        hint = self._font_hint.render(
            "↑↓ select · ENTER confirm · ESC cancel", True, C_HINT)
        screen.blit(hint, (mx + PAD, y + 8))
