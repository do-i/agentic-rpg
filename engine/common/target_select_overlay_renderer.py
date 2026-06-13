# engine/common/target_select_overlay_renderer.py
#
# Reusable party target picker rendered as a modal overlay, styled to match
# the field menu (themed panel, icon rows, stat bars).

from __future__ import annotations

import pygame
from engine.common.color_constants import HP_LOW_THRESHOLD
from engine.common.font_provider import get_fonts
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    PANEL_DARK,
    TEAL,
    draw_stat_bar,
    member_icon_path,
    render_hint,
    render_icon_row,
    render_modal,
)
from engine.party.member_state import MemberState

# ── Bar colors ────────────────────────────────────────────────
C_HP_OK   = (132, 196, 111)
C_HP_LOW  = (203, 82, 47)
C_MP      = TEAL

# ── Layout ────────────────────────────────────────────────────
MODAL_W    = 640
ROW_H      = 62
ROW_GAP    = 8
PAD        = 20
HEADER_H   = 52
FOOTER_H   = 34
WARN_H     = 38
BAR_H      = 6


class TargetSelectOverlay:
    """
    Reusable party target picker rendered as an overlay.
    Caller supplies a filtered list of valid targets.

    warning: if non-empty, shown as a gold bar above the confirm hint.
             Set after apply() returns a warn-and-allow message.
    """

    def __init__(
        self,
        targets: list[MemberState],
        item_label: str,
        on_confirm: callable,
        on_cancel: callable,
        warning: str = "",
        *,
        sfx_manager,
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
        f = get_fonts()
        self._font_title  = f.get(20, bold=True)
        self._font_name   = f.get(18, bold=True)
        self._font_meta   = f.get(13)
        self._font_hint   = f.get(14)
        self._font_warn   = f.get(14, bold=True)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self._move(-1)
            elif event.key == pygame.K_DOWN:
                self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._targets:
                    self._sfx_manager.play("confirm")
                    self._on_confirm(self._targets[self._sel])
            elif event.key == pygame.K_ESCAPE:
                self._sfx_manager.play("cancel")
                self._on_cancel()

    def _move(self, delta: int) -> None:
        old = self._sel
        self._sel = (self._sel + delta) % max(len(self._targets), 1)
        if self._sel != old:
            self._sfx_manager.play("hover")

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        rows   = max(len(self._targets), 1)
        warn_h = WARN_H + 6 if self.warning else 0
        body_h = rows * (ROW_H + ROW_GAP)
        mh     = HEADER_H + body_h + warn_h + FOOTER_H + PAD

        modal = render_modal(
            screen, MODAL_W, mh,
            title=f"Use  {self._item_label}  ·  Select Target",
            title_font=self._font_title,
        )

        row_x = modal.x + 16
        row_w = MODAL_W - 32
        row_y = modal.y + HEADER_H
        if not self._targets:
            render_hint(screen, self._font_hint, "No valid targets.",
                        row_x + 4, row_y + 8)
        else:
            for i, member in enumerate(self._targets):
                self._draw_row(screen, member, row_x, row_y, row_w,
                               selected=(i == self._sel))
                row_y += ROW_H + ROW_GAP

        footer_y = modal.bottom - FOOTER_H + 6
        if self.warning:
            self._draw_warning(screen, row_x, row_w, footer_y - WARN_H - 4)
        render_hint(screen, self._font_hint,
                    "UP/DOWN select   ·   ENTER confirm   ·   ESC cancel",
                    row_x + 4, footer_y, color=DIM)

    def _draw_row(self, screen: pygame.Surface, member: MemberState,
                  x: int, y: int, w: int, selected: bool) -> None:
        is_ko = member.hp <= 0
        if is_ko:
            color = DIM
        elif selected:
            color = INK
        else:
            color = MUTED

        if member.mp_max > 0:
            subtext = f"HP {member.hp}/{member.hp_max}    MP {member.mp}/{member.mp_max}"
        else:
            subtext = f"HP {member.hp}/{member.hp_max}"

        rect = pygame.Rect(x, y, w, ROW_H)
        render_icon_row(
            screen, self._font_name, rect, member.name,
            icon_key=f"member_{member.id}",
            image_path=member_icon_path(member.id),
            focused=selected,
            dimmed_sel=False,
            color=color,
            right_text=member.class_name.title(),
            right_font=self._font_meta,
            subtext=subtext,
            sub_font=self._font_meta,
            badge="KO" if is_ko else "",
        )
        if is_ko:
            return

        bar_y = rect.bottom - 9
        bar_w = max(70, w // 4)
        bar_x = x + 64
        hp_col = C_HP_LOW if member.hp / member.hp_max < HP_LOW_THRESHOLD else C_HP_OK
        draw_stat_bar(screen, pygame.Rect(bar_x, bar_y, bar_w, BAR_H),
                      member.hp, member.hp_max, hp_col)
        if member.mp_max > 0:
            draw_stat_bar(screen, pygame.Rect(bar_x + bar_w + 10, bar_y, bar_w, BAR_H),
                          member.mp, member.mp_max, C_MP)

    def _draw_warning(self, screen: pygame.Surface, x: int, w: int, y: int) -> None:
        surf = pygame.Surface((w, WARN_H), pygame.SRCALPHA)
        pygame.draw.rect(surf, PANEL_DARK, surf.get_rect(), border_radius=5)
        pygame.draw.rect(surf, GOLD, surf.get_rect().inflate(-1, -1), 1, border_radius=5)
        screen.blit(surf, (x, y))
        msg = self._font_warn.render(f"!  {self.warning}", True, GOLD)
        screen.blit(msg, (x + 12, y + (WARN_H - msg.get_height()) // 2))
