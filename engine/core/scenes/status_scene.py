# engine/core/scenes/status_scene.py
#
# Phase 2 — Party status overview (list screen).
# Detail panel (per-member abilities + full equipment) added in next iteration.

from __future__ import annotations

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.party_state import MemberState

# ── Layout constants ──────────────────────────────────────────
BG_COLOR        = (26, 26, 46)
ROW_COLOR_SEL   = (42, 42, 74)
ROW_COLOR_NORM  = (34, 34, 34)
BORDER_SEL      = (74, 74, 122)
BORDER_NORM     = (51, 51, 51)
HEADER_COLOR    = (212, 200, 138)
MUTED           = (102, 102, 102)
TEXT_PRIMARY    = (238, 238, 238)
TEXT_SECONDARY  = (170, 170, 170)
TEXT_DIM        = (85, 85, 85)

HP_BAR_OK       = (74, 170, 74)
HP_BAR_LOW      = (170, 74, 74)
HP_TEXT_LOW     = (238, 106, 106)
MP_BAR          = (74, 74, 238)
EXP_BAR         = (106, 138, 238)

HP_LOW_THRESHOLD = 0.35   # below this → red

PAD_X           = 20
PAD_Y           = 16
ROW_H           = 58
ROW_GAP         = 6
HEADER_H        = 40
FOOTER_H        = 28

# Column x-offsets (relative to PAD_X + 20 gutter for cursor)
COL_GUTTER      = 20    # cursor gutter width
COL_NAME_W      = 110
COL_EXP_W       = 120
COL_HPMP_W      = 160
COL_STATS_W     = 120
COL_WEAP_W      = 110
COL_ARMOR_W     = 110

BAR_H           = 4
PORTRAIT_SIZE   = 32


class StatusScene(Scene):
    """
    Full-screen party status overview.
    All members visible simultaneously as a scrollable list.
    Opened with S key from field or battle menu.
    ENTER → detail panel (stub — next iteration).
    ESC / S → close and return to previous scene.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        return_scene_name: str = "world_map",
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._return_scene_name = return_scene_name

        self._selected = 0
        self._fonts_ready = False

    # ── Font init (deferred — pygame must be running) ─────────

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_header = pygame.font.SysFont("Arial", 10)
        self._font_name   = pygame.font.SysFont("Arial", 13)
        self._font_class  = pygame.font.SysFont("Arial", 11)
        self._font_stat   = pygame.font.SysFont("Arial", 10)
        self._font_hint   = pygame.font.SysFont("Arial", 11)
        self._font_gp     = pygame.font.SysFont("Arial", 12)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        state = self._holder.get()
        members = state.party.members

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_s, pygame.K_ESCAPE):
                self._close()
            elif event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(members) - 1, self._selected + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_detail()   # stub — next iteration

    def _close(self) -> None:
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    def _open_detail(self) -> None:
        pass   # stub — detail panel, next iteration

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(BG_COLOR)
        state = self._holder.get()
        members = state.party.members

        self._draw_header(screen)
        self._draw_col_headers(screen)

        row_y = PAD_Y + HEADER_H + 20   # below title + col headers
        for i, member in enumerate(members):
            self._draw_row(screen, member, i, row_y, selected=(i == self._selected))
            row_y += ROW_H + ROW_GAP

        self._draw_footer(screen, state.repository.gp)

    def _draw_header(self, screen: pygame.Surface) -> None:
        title = self._font_title.render("STATUS", True, HEADER_COLOR)
        screen.blit(title, (PAD_X, PAD_Y))

        hint = self._font_hint.render("S — close", True, MUTED)
        screen.blit(hint, (Settings.SCREEN_WIDTH - hint.get_width() - PAD_X, PAD_Y + 2))

        pygame.draw.line(
            screen, (68, 68, 68),
            (PAD_X, PAD_Y + HEADER_H - 4),
            (Settings.SCREEN_WIDTH - PAD_X, PAD_Y + HEADER_H - 4),
        )

    def _draw_col_headers(self, screen: pygame.Surface) -> None:
        y = PAD_Y + HEADER_H + 2
        x = PAD_X + COL_GUTTER
        labels = ["NAME", "EXP", "HP / MP", "STATS", "WEAPON / SHIELD", "ARMOR"]
        widths = [COL_NAME_W, COL_EXP_W, COL_HPMP_W, COL_STATS_W, COL_WEAP_W, COL_ARMOR_W]
        for label, w in zip(labels, widths):
            surf = self._font_header.render(label, True, MUTED)
            screen.blit(surf, (x, y))
            x += w + 12

    # ── Row ───────────────────────────────────────────────────

    def _draw_row(
        self,
        screen: pygame.Surface,
        member: MemberState,
        index: int,
        y: int,
        selected: bool,
    ) -> None:
        row_w = Settings.SCREEN_WIDTH - PAD_X * 2
        bg    = ROW_COLOR_SEL if selected else ROW_COLOR_NORM
        bdr   = BORDER_SEL   if selected else BORDER_NORM
        pygame.draw.rect(screen, bg,  (PAD_X, y, row_w, ROW_H), border_radius=4)
        pygame.draw.rect(screen, bdr, (PAD_X, y, row_w, ROW_H), 1, border_radius=4)

        # cursor
        if selected:
            cur = self._font_stat.render("▶", True, HEADER_COLOR)
            screen.blit(cur, (PAD_X + 6, y + ROW_H // 2 - cur.get_height() // 2))

        x = PAD_X + COL_GUTTER
        x = self._draw_col_name(screen, member, x, y)
        x = self._draw_col_exp(screen, member, x, y)
        x = self._draw_col_hpmp(screen, member, x, y)
        x = self._draw_col_stats(screen, member, x, y)
        x = self._draw_col_weapon(screen, member, x, y)
        self._draw_col_armor(screen, member, x, y)

    # ── Columns ───────────────────────────────────────────────

    def _draw_col_name(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        initials = "".join(w[0].upper() for w in m.name.split()[:2])
        # portrait box
        port_rect = (x, y + (ROW_H - PORTRAIT_SIZE) // 2, PORTRAIT_SIZE, PORTRAIT_SIZE)
        pygame.draw.rect(screen, (50, 50, 80), port_rect, border_radius=3)
        pygame.draw.rect(screen, (90, 90, 130), port_rect, 1, border_radius=3)
        init_surf = self._font_stat.render(initials, True, TEXT_SECONDARY)
        screen.blit(init_surf, (
            port_rect[0] + PORTRAIT_SIZE // 2 - init_surf.get_width() // 2,
            port_rect[1] + PORTRAIT_SIZE // 2 - init_surf.get_height() // 2,
        ))
        # name + class
        tx = x + PORTRAIT_SIZE + 8
        name_surf = self._font_name.render(m.name, True, TEXT_PRIMARY)
        screen.blit(name_surf, (tx, y + 12))
        cls_surf = self._font_class.render(m.class_name, True, TEXT_SECONDARY)
        screen.blit(cls_surf, (tx, y + 28))
        return x + COL_NAME_W + 12

    def _draw_col_exp(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        pct = m.exp_pct
        lv_text = f"Lv {m.level} · {int(pct * 100)}%"
        lv_surf = self._font_stat.render(lv_text, True, TEXT_SECONDARY)
        screen.blit(lv_surf, (x, y + 14))
        bar_y = y + 30
        bar_w = COL_EXP_W - 4
        pygame.draw.rect(screen, (17, 17, 46), (x, bar_y, bar_w, BAR_H), border_radius=2)
        pygame.draw.rect(screen, EXP_BAR, (x, bar_y, int(bar_w * pct), BAR_H), border_radius=2)
        return x + COL_EXP_W + 12

    def _draw_col_hpmp(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        bar_w = 80
        val_x = x + bar_w + 6

        # HP
        hp_pct  = m.hp / m.hp_max if m.hp_max > 0 else 0
        low_hp  = hp_pct < HP_LOW_THRESHOLD
        hp_col  = HP_BAR_LOW if low_hp else HP_BAR_OK
        hp_tcol = HP_TEXT_LOW if low_hp else TEXT_SECONDARY

        hp_lbl = self._font_stat.render("HP", True, (122, 170, 122))
        screen.blit(hp_lbl, (x, y + 13))
        bx = x + 18
        pygame.draw.rect(screen, (17, 17, 46), (bx, y + 15, bar_w, BAR_H), border_radius=2)
        pygame.draw.rect(screen, hp_col,       (bx, y + 15, int(bar_w * hp_pct), BAR_H), border_radius=2)
        hp_val = self._font_stat.render(f"{m.hp}/{m.hp_max}", True, hp_tcol)
        screen.blit(hp_val, (bx + bar_w + 4, y + 11))

        # MP
        if m.mp_max > 0:
            mp_pct = m.mp / m.mp_max
            mp_lbl = self._font_stat.render("MP", True, (122, 122, 238))
            screen.blit(mp_lbl, (x, y + 33))
            pygame.draw.rect(screen, (17, 17, 46), (bx, y + 35, bar_w, BAR_H), border_radius=2)
            pygame.draw.rect(screen, MP_BAR,       (bx, y + 35, int(bar_w * mp_pct), BAR_H), border_radius=2)
            mp_val = self._font_stat.render(f"{m.mp}/{m.mp_max}", True, TEXT_SECONDARY)
            screen.blit(mp_val, (bx + bar_w + 4, y + 31))
        else:
            mp_lbl = self._font_stat.render("MP", True, TEXT_DIM)
            screen.blit(mp_lbl, (x, y + 33))
            mp_dash = self._font_stat.render("—", True, TEXT_DIM)
            screen.blit(mp_dash, (bx + bar_w + 4, y + 31))

        return x + COL_HPMP_W + 12

    def _draw_col_stats(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        lines = [
            (f"STR", f"{m.str_}"),
            (f"DEX", f"{m.dex}"),
            (f"CON", f"{m.con}"),
            (f"INT", f"{m.int_}"),
        ]
        col2_x = x + 36
        for i, (label, val) in enumerate(lines):
            row_y = y + 8 + i * 11
            lbl_s = self._font_stat.render(label, True, TEXT_SECONDARY)
            val_s = self._font_stat.render(val,   True, TEXT_PRIMARY)
            screen.blit(lbl_s, (x,      row_y))
            screen.blit(val_s, (col2_x, row_y))
        return x + COL_STATS_W + 12

    def _draw_col_weapon(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        weapon = m.equipped.get("weapon", "—")
        shield = m.equipped.get("shield", "—")
        w_surf = self._font_stat.render(weapon if weapon else "—", True,
                                        TEXT_PRIMARY if weapon else TEXT_DIM)
        s_surf = self._font_stat.render(shield if shield else "—", True,
                                        TEXT_SECONDARY if shield else TEXT_DIM)
        screen.blit(w_surf, (x, y + 14))
        screen.blit(s_surf, (x, y + 28))
        return x + COL_WEAP_W + 12

    def _draw_col_armor(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> None:
        helmet    = m.equipped.get("helmet",    "")
        body      = m.equipped.get("body",      "")
        accessory = m.equipped.get("accessory", "")
        slots = [
            (helmet,    TEXT_SECONDARY),
            (body,      TEXT_PRIMARY),
            (accessory, TEXT_SECONDARY),
        ]
        for i, (val, col) in enumerate(slots):
            text = val if val else "—"
            tcol = col if val else TEXT_DIM
            surf = self._font_stat.render(text, True, tcol)
            screen.blit(surf, (x, y + 8 + i * 14))

    # ── Footer ────────────────────────────────────────────────

    def _draw_footer(self, screen: pygame.Surface, gp: int) -> None:
        fy = Settings.SCREEN_HEIGHT - FOOTER_H
        pygame.draw.line(screen, (51, 51, 51),
                         (PAD_X, fy), (Settings.SCREEN_WIDTH - PAD_X, fy))

        hint = self._font_hint.render("↑↓ select · ENTER detail · S close", True, MUTED)
        screen.blit(hint, (PAD_X, fy + 8))

        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gp_val   = self._font_gp.render(f"{gp:,}", True, TEXT_PRIMARY)
        gx = Settings.SCREEN_WIDTH - PAD_X - gp_val.get_width()
        screen.blit(gp_val,   (gx, fy + 8))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, fy + 8))
