# engine/ui/status_renderer.py
#
# Status scene rendering — all drawing, fonts, portrait loading, layout.
# Extracted from status_scene.py to separate rendering from game logic.

from __future__ import annotations

import pygame
from engine.common.font_provider import get_fonts

from engine.party.member_state import MemberState
from engine.party.party_state import exp_pct
from engine.common.color_constants import HP_LOW_THRESHOLD
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED as THEME_MUTED,
    TEAL,
    VIOLET,
    draw_divider,
    icon_surface,
    member_icon_path,
    render_backdrop,
    render_header,
    render_hint,
    render_modal,
    render_row_frame,
)

# ── Colors (field-menu theme) ─────────────────────────────────
TEXT_PRIMARY    = INK
TEXT_SECONDARY  = THEME_MUTED
HEADER_COLOR    = GOLD
MUTED           = THEME_MUTED
TEXT_DIM        = DIM
HP_BAR_OK       = (132, 196, 111)
HP_BAR_LOW      = (203, 82, 47)
HP_TEXT_LOW     = (224, 122, 96)
MP_BAR          = TEAL
EXP_BAR         = VIOLET
BAR_TRACK       = (17, 17, 22)

C_SPELL_DIS     = (90, 84, 72)
C_MP_COST       = TEAL
C_TOAST         = (132, 196, 111)

PAD_X    = 20
PAD_Y    = 16
ROW_GAP  = 14          # matches the field-menu / equipment card spacing
ROW_H_MAX = 118        # cap so a small party keeps reasonable card height
HEADER_H = 40
FOOTER_H = 28

PORTRAIT_MAX = 92      # matches the equipment party portrait size
BAR_H        = 10

COL_GUTTER  = 22
COL_NAME_W  = 155
COL_EXP_W   = 140
COL_HPMP_W  = 195
COL_STATS_W = 125


class StatusRenderer:
    """Handles all rendering for the status scene."""

    def __init__(self, scenario_path: str) -> None:
        self._scenario_path = scenario_path
        self._fonts_ready = False

    @property
    def fonts_ready(self) -> bool:
        return self._fonts_ready

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(20, bold=True)
        self._font_name  = f.get(18, bold=True)
        self._font_class = f.get(15)
        self._font_level = f.get(15)
        self._font_stat  = f.get(14)
        self._font_hint  = f.get(14)
        self._font_gp    = f.get(17)
        self._font_spell = f.get(15)
        self._font_spell_title = f.get(16, bold=True)
        self._font_toast = f.get(18, bold=True)
        self._fonts_ready = True

    # ── Main render ───────────────────────────────────────────

    def render(self, screen: pygame.Surface, members: list[MemberState],
               gp: int, selected: int,
               spell_list: list[dict] | None, spell_sel: int,
               spell_caster: MemberState | None,
               target_overlay, popup_text: str, popup_active: bool) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)
        self._draw_header(screen, gp)

        if not members:
            s = self._font_stat.render("No party members.", True, TEXT_DIM)
            screen.blit(s, (PAD_X, PAD_Y + HEADER_H + 8))
            self._draw_footer(screen)
            return

        # Distribute member cards down the full height between the header
        # divider and the footer, so portraits fill the vertical space the
        # same way the equipment party panel does.
        top = PAD_Y + HEADER_H
        bottom = screen.get_height() - FOOTER_H - 10
        n = len(members)
        row_h = min(ROW_H_MAX, (bottom - top - ROW_GAP * (n - 1)) // n)
        portrait = min(row_h - 16, PORTRAIT_MAX)

        row_y = top
        for i, member in enumerate(members):
            self._draw_row(screen, member, i, row_y, row_h, portrait,
                           selected=(i == selected))
            row_y += row_h + ROW_GAP

        self._draw_footer(screen)

        if spell_list is not None:
            self._draw_spell_menu(screen, spell_list, spell_sel, spell_caster)
        if target_overlay:
            target_overlay.render(screen)
        if popup_active:
            self._draw_popup(screen, popup_text)

    def _draw_header(self, screen: pygame.Surface, gp: int) -> None:
        render_header(screen, self._font_title, self._font_hint,
                      "STATUS", "party roster and growth", PAD_X, PAD_Y - 6)
        gp_val   = self._font_gp.render(f"{gp:,}", True, TEXT_PRIMARY)
        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gx = screen.get_width() - PAD_X - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD_Y + 2))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD_Y + 2))
        draw_divider(screen, PAD_X, PAD_Y + HEADER_H - 4,
                     screen.get_width() - PAD_X * 2)

    def _draw_row(self, screen, m: MemberState, index: int, y: int,
                  row_h: int, portrait: int, selected: bool) -> None:
        row_w = screen.get_width() - PAD_X * 2
        render_row_frame(screen, pygame.Rect(PAD_X, y, row_w, row_h), focused=selected)

        x = PAD_X + COL_GUTTER
        x = self._draw_portrait_name(screen, m, x, y, row_h, portrait)
        x = self._draw_exp(screen, m, x, y, row_h)
        x = self._draw_hpmp(screen, m, x, y, row_h)
        x = self._draw_stats(screen, m, x, y, row_h)
        self._draw_gear(screen, m, x, y, row_h)

    def _draw_portrait_name(self, screen, m: MemberState, x: int, y: int,
                            row_h: int, portrait: int) -> int:
        port_y = y + (row_h - portrait) // 2
        icon = icon_surface(f"member_{m.id}", portrait, image_path=member_icon_path(m.id))
        screen.blit(icon, (x, port_y))

        tx = x + portrait + 12
        content_h = self._font_name.get_height() + 6 + self._font_class.get_height()
        ty = y + (row_h - content_h) // 2
        screen.blit(self._font_name.render(m.name, True, TEXT_PRIMARY), (tx, ty))
        class_label = f"{m.class_name}  ·  {m.row.upper()}"
        screen.blit(self._font_class.render(class_label, True, HEADER_COLOR),
                    (tx, ty + self._font_name.get_height() + 4))
        return x + COL_NAME_W + 50

    def _draw_exp(self, screen, m: MemberState, x: int, y: int, row_h: int) -> int:
        bar_w  = COL_EXP_W
        line_h = self._font_stat.get_height()
        cy     = y + (row_h - (line_h * 2 + BAR_H + 20)) // 2

        screen.blit(self._font_level.render(f"Lv {m.level}", True, TEXT_PRIMARY), (x, cy))
        bar_y = cy + line_h + 10
        pygame.draw.rect(screen, BAR_TRACK, (x, bar_y, bar_w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, EXP_BAR,
                         (x, bar_y, int(bar_w * exp_pct(m)), BAR_H), border_radius=3)
        screen.blit(self._font_stat.render(f"{m.exp}/{m.exp_next}", True, TEXT_SECONDARY),
                    (x, cy + line_h + 25))
        return x + COL_EXP_W + 12

    def _draw_hpmp(self, screen, m: MemberState, x: int, y: int, row_h: int) -> int:
        bar_w  = 100
        lbl_w  = 28
        line_h = self._font_stat.get_height()
        block_h = line_h + 4 + BAR_H
        cy = y + (row_h - block_h * 2 - 10) // 2

        hp_pct  = m.hp / m.hp_max if m.hp_max > 0 else 0
        low_hp  = hp_pct < HP_LOW_THRESHOLD
        hp_col  = HP_BAR_LOW if low_hp else HP_BAR_OK
        hp_tcol = HP_TEXT_LOW if low_hp else TEXT_SECONDARY
        screen.blit(self._font_stat.render("HP", True, HP_BAR_OK), (x, cy))
        screen.blit(self._font_stat.render(f"{m.hp}/{m.hp_max}", True, hp_tcol),
                    (x + lbl_w + bar_w + 10, cy))
        pygame.draw.rect(screen, BAR_TRACK, (x + lbl_w + 5, cy + 4, bar_w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, hp_col,
                         (x + lbl_w + 5, cy + 4, int(bar_w * hp_pct), BAR_H), border_radius=3)

        mp_y = cy + block_h + 10
        if m.mp_max > 0:
            mp_pct = m.mp / m.mp_max
            screen.blit(self._font_stat.render("MP", True, MP_BAR), (x, mp_y))
            screen.blit(self._font_stat.render(f"{m.mp}/{m.mp_max}", True, TEXT_SECONDARY),
                        (x + lbl_w + bar_w + 10, mp_y))
            pygame.draw.rect(screen, BAR_TRACK,
                             (x + lbl_w + 5, mp_y + 4, bar_w, BAR_H), border_radius=3)
            pygame.draw.rect(screen, MP_BAR,
                             (x + lbl_w + 5, mp_y + 4, int(bar_w * mp_pct), BAR_H), border_radius=3)
        else:
            screen.blit(self._font_stat.render("MP", True, TEXT_DIM), (x, mp_y))
            screen.blit(self._font_stat.render("-", True, TEXT_DIM), (x + lbl_w + 4, mp_y))

        return x + COL_HPMP_W + 25

    def _draw_stats(self, screen, m: MemberState, x: int, y: int, row_h: int) -> int:
        lines  = [("STR", str(m.str_)), ("DEX", str(m.dex)),
                  ("CON", str(m.con)),  ("INT", str(m.int_))]
        line_h = self._font_stat.get_height() + 6
        cy     = y + (row_h - len(lines) * line_h) // 2
        col2_x = x + 38
        for i, (label, val) in enumerate(lines):
            ry = cy + i * line_h
            screen.blit(self._font_stat.render(label, True, TEXT_SECONDARY), (x,      ry))
            screen.blit(self._font_stat.render(val,   True, TEXT_PRIMARY),   (col2_x, ry))
        return x + COL_STATS_W + 12

    def _draw_gear(self, screen, m: MemberState, x: int, y: int, row_h: int) -> None:
        slots  = [("Helm",  m.equipped.get("helmet",    "")),
                  ("Body",  m.equipped.get("body",      "")),
                  ("Wpn",   m.equipped.get("weapon",    "")),
                  ("Shld",  m.equipped.get("shield",    "")),
                  ("Acc",   m.equipped.get("accessory", ""))]
        line_h = self._font_stat.get_height() + 5
        cy     = y + (row_h - len(slots) * line_h) // 2
        for i, (lbl, val) in enumerate(slots):
            ry = cy + i * line_h
            screen.blit(self._font_stat.render(lbl, True, MUTED), (x, ry))
            screen.blit(self._font_stat.render(
                val or "-", True, TEXT_SECONDARY if val else TEXT_DIM), (x + 50, ry))

    # ── Spell menu overlay ────────────────────────────────────

    def _draw_spell_menu(self, screen: pygame.Surface,
                         spells: list[dict], spell_sel: int,
                         caster: MemberState | None) -> None:
        if not spells or not caster:
            return

        row_h  = 38
        gap    = 6
        pad    = 16
        w      = 360
        h      = pad + 32 + len(spells) * (row_h + gap) + pad + 14
        modal  = render_modal(screen, w, h,
                              title=f"{caster.name}  Spells",
                              title_font=self._font_spell_title)
        x, y = modal.x, modal.y

        mp_s = self._font_spell.render(f"MP {caster.mp}/{caster.mp_max}", True, C_MP_COST)
        screen.blit(mp_s, (x + w - mp_s.get_width() - pad, y + 16))

        ry = y + pad + 32
        for i, spell in enumerate(spells):
            sel      = (i == spell_sel)
            cost     = spell["mp_cost"]
            disabled = cost > caster.mp

            rect = pygame.Rect(x + 8, ry, w - 16, row_h)
            render_row_frame(screen, rect, focused=sel)

            name_c = C_SPELL_DIS if disabled else (TEXT_PRIMARY if sel else TEXT_SECONDARY)
            name_s = self._font_spell.render(spell["name"], True, name_c)
            screen.blit(name_s, (rect.x + 16, ry + (row_h - name_s.get_height()) // 2))

            cost_c = C_SPELL_DIS if disabled else C_MP_COST
            cost_s = self._font_spell.render(f"{cost} MP", True, cost_c)
            screen.blit(cost_s, (rect.right - cost_s.get_width() - 14,
                                  ry + (row_h - cost_s.get_height()) // 2))
            ry += row_h + gap

        render_hint(screen, self._font_hint, "ENTER cast \u00b7 ESC back",
                    x + pad, y + h - pad - self._font_hint.get_height() + 4)

    # ── Popup ─────────────────────────────────────────────────

    def _draw_popup(self, screen: pygame.Surface, popup_text: str) -> None:
        pw, ph = 360, 88
        modal = render_modal(screen, pw, ph)
        msg = self._font_toast.render(popup_text, True, C_TOAST)
        screen.blit(msg, (modal.x + (pw - msg.get_width()) // 2, modal.y + 18))
        hint = self._font_hint.render("ENTER / ESC  close", True, MUTED)
        screen.blit(hint, (modal.x + (pw - hint.get_width()) // 2, modal.bottom - 28))

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = screen.get_height() - FOOTER_H
        draw_divider(screen, PAD_X, fy, screen.get_width() - PAD_X * 2)
        render_hint(screen, self._font_hint,
                    "select \u00b7 ENTER spells \u00b7 R row \u00b7 S close",
                    PAD_X, fy + 8)
