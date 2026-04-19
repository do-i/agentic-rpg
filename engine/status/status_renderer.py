# engine/ui/status_renderer.py
#
# Status scene rendering — all drawing, fonts, portrait loading, layout.
# Extracted from status_scene.py to separate rendering from game logic.

from __future__ import annotations

from pathlib import Path
import pygame
from engine.common.font_provider import get_fonts

from engine.party.member_state import MemberState
from engine.party.party_state import exp_pct
from engine.common.color_constants import (
    C_TEXT as TEXT_PRIMARY,
    C_TEXT_MUT as TEXT_SECONDARY,
    HP_LOW_THRESHOLD,
)

# ── Colors ────────────────────────────────────────────────────
BG_COLOR        = (26, 26, 46)
ROW_COLOR_SEL   = (42, 42, 74)
ROW_COLOR_NORM  = (34, 34, 34)
BORDER_SEL      = (74, 74, 122)
BORDER_NORM     = (51, 51, 51)
HEADER_COLOR    = (212, 200, 138)
MUTED           = (102, 102, 102)
TEXT_DIM        = (85, 85, 85)
HP_BAR_OK       = (74, 170, 74)
HP_BAR_LOW      = (170, 74, 74)
HP_TEXT_LOW     = (238, 106, 106)
MP_BAR          = (74, 74, 238)
EXP_BAR         = (106, 138, 238)

C_SPELL_BG      = (22, 22, 44)
C_SPELL_BDR     = (120, 110, 180)
C_SPELL_SEL     = (45, 42, 75)
C_SPELL_DIS     = (70, 70, 80)
C_MP_COST       = (130, 130, 220)
C_TOAST         = (100, 220, 130)

PAD_X    = 20
PAD_Y    = 16
ROW_H    = 120
ROW_GAP  = 4
HEADER_H = 40
FOOTER_H = 28

PORTRAIT_SIZE = 100
BAR_H         = 10

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
        self._portraits: dict[str, pygame.Surface] = {}

    @property
    def fonts_ready(self) -> bool:
        return self._fonts_ready

    def _load_portrait(self, member_id: str) -> pygame.Surface | None:
        if member_id in self._portraits:
            return self._portraits[member_id]
        path = Path(self._scenario_path) / "assets" / "images" / f"{member_id}_profile.png"
        if not path.exists():
            return None
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            img = pygame.transform.scale(img, (PORTRAIT_SIZE, PORTRAIT_SIZE))
            self._portraits[member_id] = img
            return img
        except Exception:
            return None

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

        screen.fill(BG_COLOR)
        self._draw_header(screen, gp)

        if not members:
            s = self._font_stat.render("No party members.", True, TEXT_DIM)
            screen.blit(s, (PAD_X, PAD_Y + HEADER_H + 8))
            self._draw_footer(screen)
            return

        row_y = PAD_Y + HEADER_H
        for i, member in enumerate(members):
            self._draw_row(screen, member, i, row_y, selected=(i == selected))
            row_y += ROW_H + ROW_GAP

        self._draw_footer(screen)

        if spell_list is not None:
            self._draw_spell_menu(screen, spell_list, spell_sel, spell_caster)
        if target_overlay:
            target_overlay.render(screen)
        if popup_active:
            self._draw_popup(screen, popup_text)

    def _draw_header(self, screen: pygame.Surface, gp: int) -> None:
        screen.blit(self._font_title.render("STATUS", True, HEADER_COLOR), (PAD_X, PAD_Y))
        gp_val   = self._font_gp.render(f"{gp:,}", True, TEXT_PRIMARY)
        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gx = screen.get_width() - PAD_X - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD_Y + 2))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD_Y + 2))
        pygame.draw.line(screen, (68, 68, 68),
                         (PAD_X, PAD_Y + HEADER_H - 4),
                         (screen.get_width() - PAD_X, PAD_Y + HEADER_H - 4))

    def _draw_row(self, screen, m: MemberState, index: int, y: int, selected: bool) -> None:
        row_w = screen.get_width() - PAD_X * 2
        bg  = ROW_COLOR_SEL if selected else ROW_COLOR_NORM
        bdr = BORDER_SEL    if selected else BORDER_NORM
        pygame.draw.rect(screen, bg,  (PAD_X, y, row_w, ROW_H), border_radius=4)
        pygame.draw.rect(screen, bdr, (PAD_X, y, row_w, ROW_H), 1, border_radius=4)

        if selected:
            cur = self._font_stat.render(" ", True, HEADER_COLOR)
            screen.blit(cur, (PAD_X + 6, y + ROW_H // 2 - cur.get_height() // 2))

        x = PAD_X + COL_GUTTER
        x = self._draw_portrait_name(screen, m, x, y)
        x = self._draw_exp(screen, m, x, y)
        x = self._draw_hpmp(screen, m, x, y)
        x = self._draw_stats(screen, m, x, y)
        self._draw_gear(screen, m, x, y)

    def _draw_portrait_name(self, screen, m: MemberState, x: int, y: int) -> int:
        port_y    = y + (ROW_H - PORTRAIT_SIZE) // 2
        port_rect = (x, port_y, PORTRAIT_SIZE, PORTRAIT_SIZE)
        img = self._load_portrait(m.id)
        if img:
            screen.blit(img, (x, port_y))
        else:
            pygame.draw.rect(screen, (50, 50, 80), port_rect, border_radius=4)
            pygame.draw.rect(screen, (90, 90, 130), port_rect, 1, border_radius=4)
            initials = "".join(w[0].upper() for w in m.name.split()[:2])
            s = self._font_stat.render(initials, True, TEXT_SECONDARY)
            screen.blit(s, (x + PORTRAIT_SIZE // 2 - s.get_width() // 2,
                             port_y + PORTRAIT_SIZE // 2 - s.get_height() // 2))

        tx = x + PORTRAIT_SIZE + 10
        content_h = self._font_name.get_height() + 6 + self._font_class.get_height()
        ty = y + (ROW_H - content_h) // 2
        screen.blit(self._font_name.render(m.name, True, TEXT_PRIMARY), (tx, ty))
        screen.blit(self._font_class.render(m.class_name, True, TEXT_SECONDARY),
                    (tx, ty + self._font_name.get_height() + 4))
        return x + COL_NAME_W + 50

    def _draw_exp(self, screen, m: MemberState, x: int, y: int) -> int:
        bar_w  = COL_EXP_W
        line_h = self._font_stat.get_height()
        cy     = y + (ROW_H - (line_h * 2 + BAR_H + 20)) // 2

        screen.blit(self._font_level.render(f"Lv {m.level}", True, TEXT_PRIMARY), (x, cy))
        bar_y = cy + line_h + 10
        pygame.draw.rect(screen, (17, 17, 46), (x, bar_y, bar_w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, EXP_BAR,
                         (x, bar_y, int(bar_w * exp_pct(m)), BAR_H), border_radius=3)
        screen.blit(self._font_stat.render(f"{m.exp}/{m.exp_next}", True, TEXT_SECONDARY),
                    (x, cy + line_h + 25))
        return x + COL_EXP_W + 12

    def _draw_hpmp(self, screen, m: MemberState, x: int, y: int) -> int:
        bar_w  = 100
        lbl_w  = 28
        line_h = self._font_stat.get_height()
        block_h = line_h + 4 + BAR_H
        cy = y + (ROW_H - block_h * 2 - 10) // 2

        hp_pct  = m.hp / m.hp_max if m.hp_max > 0 else 0
        low_hp  = hp_pct < HP_LOW_THRESHOLD
        hp_col  = HP_BAR_LOW if low_hp else HP_BAR_OK
        hp_tcol = HP_TEXT_LOW if low_hp else TEXT_SECONDARY
        screen.blit(self._font_stat.render("HP", True, (122, 170, 122)), (x, cy))
        screen.blit(self._font_stat.render(f"{m.hp}/{m.hp_max}", True, hp_tcol),
                    (x + lbl_w + bar_w + 10, cy))
        pygame.draw.rect(screen, (17, 17, 46), (x + lbl_w + 5, cy + 4, bar_w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, hp_col,
                         (x + lbl_w + 5, cy + 4, int(bar_w * hp_pct), BAR_H), border_radius=3)

        mp_y = cy + block_h + 10
        if m.mp_max > 0:
            mp_pct = m.mp / m.mp_max
            screen.blit(self._font_stat.render("MP", True, (122, 122, 238)), (x, mp_y))
            screen.blit(self._font_stat.render(f"{m.mp}/{m.mp_max}", True, TEXT_SECONDARY),
                        (x + lbl_w + bar_w + 10, mp_y))
            pygame.draw.rect(screen, (17, 17, 46),
                             (x + lbl_w + 5, mp_y + 4, bar_w, BAR_H), border_radius=3)
            pygame.draw.rect(screen, MP_BAR,
                             (x + lbl_w + 5, mp_y + 4, int(bar_w * mp_pct), BAR_H), border_radius=3)
        else:
            screen.blit(self._font_stat.render("MP", True, TEXT_DIM), (x, mp_y))
            screen.blit(self._font_stat.render("-", True, TEXT_DIM), (x + lbl_w + 4, mp_y))

        return x + COL_HPMP_W + 25

    def _draw_stats(self, screen, m: MemberState, x: int, y: int) -> int:
        lines  = [("STR", str(m.str_)), ("DEX", str(m.dex)),
                  ("CON", str(m.con)),  ("INT", str(m.int_))]
        line_h = self._font_stat.get_height() + 6
        cy     = y + (ROW_H - len(lines) * line_h) // 2
        col2_x = x + 38
        for i, (label, val) in enumerate(lines):
            ry = cy + i * line_h
            screen.blit(self._font_stat.render(label, True, TEXT_SECONDARY), (x,      ry))
            screen.blit(self._font_stat.render(val,   True, TEXT_PRIMARY),   (col2_x, ry))
        return x + COL_STATS_W + 12

    def _draw_gear(self, screen, m: MemberState, x: int, y: int) -> None:
        slots  = [("Helm",  m.equipped.get("helmet",    "")),
                  ("Body",  m.equipped.get("body",      "")),
                  ("Wpn",   m.equipped.get("weapon",    "")),
                  ("Shld",  m.equipped.get("shield",    "")),
                  ("Acc",   m.equipped.get("accessory", ""))]
        line_h = self._font_stat.get_height() + 5
        cy     = y + (ROW_H - len(slots) * line_h) // 2
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

        row_h  = 32
        pad    = 16
        w      = 340
        h      = pad + 28 + len(spells) * row_h + pad + 20
        x      = (screen.get_width() - w) // 2
        y      = (screen.get_height() - h) // 2

        overlay = pygame.Surface(
            (screen.get_width(), screen.get_height()), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, C_SPELL_BG,  (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, C_SPELL_BDR, (x, y, w, h), 2, border_radius=6)

        title = self._font_spell_title.render(f"{caster.name} - Spells", True, HEADER_COLOR)
        screen.blit(title, (x + pad, y + pad))

        mp_s = self._font_spell.render(f"MP {caster.mp}/{caster.mp_max}", True, C_MP_COST)
        screen.blit(mp_s, (x + w - mp_s.get_width() - pad, y + pad))

        ry = y + pad + 28
        for i, spell in enumerate(spells):
            sel      = (i == spell_sel)
            cost     = spell.get("mp_cost", 0)
            disabled = cost > caster.mp

            if sel:
                pygame.draw.rect(screen, C_SPELL_SEL, (x + 4, ry, w - 8, row_h), border_radius=3)
                cur = self._font_spell.render(" ", True, HEADER_COLOR)
                screen.blit(cur, (x + 10, ry + (row_h - cur.get_height()) // 2))

            name_c = C_SPELL_DIS if disabled else (TEXT_PRIMARY if sel else TEXT_SECONDARY)
            name_s = self._font_spell.render(spell["name"], True, name_c)
            screen.blit(name_s, (x + 28, ry + (row_h - name_s.get_height()) // 2))

            cost_c = C_SPELL_DIS if disabled else C_MP_COST
            cost_s = self._font_spell.render(f"{cost} MP", True, cost_c)
            screen.blit(cost_s, (x + w - cost_s.get_width() - pad,
                                  ry + (row_h - cost_s.get_height()) // 2))
            ry += row_h

        hint = self._font_hint.render("ENTER cast \u00b7 ESC back", True, MUTED)
        screen.blit(hint, (x + pad, y + h - pad - hint.get_height() + 4))

    # ── Popup ─────────────────────────────────────────────────

    def _draw_popup(self, screen: pygame.Surface, popup_text: str) -> None:
        pw, ph = 360, 80
        px = (screen.get_width()  - pw) // 2
        py = (screen.get_height() - ph) // 2
        pygame.draw.rect(screen, BG_COLOR,   (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(screen, BORDER_SEL, (px, py, pw, ph), 2, border_radius=6)
        msg = self._font_toast.render(popup_text, True, C_TOAST)
        screen.blit(msg, (px + (pw - msg.get_width()) // 2, py + 14))
        hint = self._font_hint.render("ENTER / ESC  close", True, MUTED)
        screen.blit(hint, (px + (pw - hint.get_width()) // 2, py + ph - 28))

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = screen.get_height() - FOOTER_H
        pygame.draw.line(screen, (51, 51, 51),
                         (PAD_X, fy), (screen.get_width() - PAD_X, fy))
        hint = self._font_hint.render("select \u00b7 ENTER spells \u00b7 S close", True, MUTED)
        screen.blit(hint, (PAD_X, fy + 8))
