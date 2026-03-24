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
# Screen: 1280×720
# Available height = 720 - PAD_Y(16) - HEADER_H(40) - FOOTER_H(28) - PAD_Y(16) = 620
# No col-header row. 5 rows × 120 + 4 gaps × 4 = 616 ✓

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

HP_LOW_THRESHOLD = 0.35

PAD_X           = 20
PAD_Y           = 16
ROW_H           = 120        # 5 × 120 + 4 × 4 = 616, fits in 620 available
ROW_GAP         = 4
HEADER_H        = 40
FOOTER_H        = 28

PORTRAIT_SIZE   = 100        # ← 100px portrait
BAR_H           = 10

COL_GUTTER      = 22
COL_NAME_W      = 155        # portrait(100) + name/class beside it
COL_EXP_W       = 140        # lv + exp/next + bar
COL_HPMP_W      = 195        # HP+MP bars
COL_STATS_W     = 125        # STR DEX CON INT
COL_GEAR_W      = 210        # combined: Helm Body Weapon Shield Acc (2 cols inside)


# ── Debug: full party stub (remove when Phase 5 populates party from YAML) ──
def _make_debug_party() -> list[MemberState]:
    return [
        MemberState(
            "hero_aric", "Aric", protagonist=True, class_name="Hero",
            level=8,  exp=6200,  exp_next=8944,
            hp=68,  hp_max=68,  mp=40, mp_max=40,
            str_=18, dex=14, con=16, int_=9,
            equipped={"weapon": "Iron Sword", "shield": "Kite Shield",
                      "helmet": "Iron Helm", "body": "Chainmail"},
        ),
        MemberState(
            "elise", "Elise", class_name="Cleric",
            level=7,  exp=4900,  exp_next=6317,
            hp=180, hp_max=180, mp=120, mp_max=140,
            str_=8,  dex=10, con=14, int_=16,
            equipped={"weapon": "Oak Staff", "body": "Linen Robe"},
        ),
        MemberState(
            "reiya", "Reiya", class_name="Sorcerer",
            level=8,  exp=6080,  exp_next=8497,
            hp=11,  hp_max=28,  mp=48, mp_max=48,
            str_=6,  dex=12, con=7,  int_=20,
            equipped={"weapon": "Oak Staff", "helmet": "Silver Circlet",
                      "body": "Silk Robe"},
        ),
        MemberState(
            "jep", "Jep", class_name="Rogue",
            level=14, exp=17606, exp_next=21213,
            hp=44,  hp_max=44,  mp=16, mp_max=16,
            str_=16, dex=26, con=13, int_=8,
            equipped={"weapon": "Dagger", "shield": "Buckler",
                      "helmet": "Leather Hood", "body": "Leather Vest"},
        ),
        MemberState(
            "kael", "Kael", class_name="Warrior",
            level=20, exp=40000, exp_next=44721,
            hp=128, hp_max=128, mp=0, mp_max=0,
            str_=28, dex=14, con=26, int_=5,
            equipped={"weapon": "Iron Sword", "shield": "Iron Shield",
                      "body": "Chainmail"},
        ),
    ]


class StatusScene(Scene):
    """
    Full-screen party status overview.
    5 rows fill the screen. No scroll — party is fixed at ≤5 members.
    S / ESC → close and return to previous scene.
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

    # ── Font init ─────────────────────────────────────────────

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 20, bold=True)
        self._font_name   = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_class  = pygame.font.SysFont("Arial", 15)
        self._font_stat   = pygame.font.SysFont("Arial", 14)
        self._font_hint   = pygame.font.SysFont("Arial", 14)
        self._font_gp     = pygame.font.SysFont("Arial", 17)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        state = self._holder.get()
        members = self._get_members(state)

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
                pass  # detail panel — next iteration

    def _close(self) -> None:
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    def _get_members(self, state) -> list[MemberState]:
        """Return debug party when real party has only protagonist (Phase 5 not done)."""
        members = state.party.members
        if len(members) <= 1:
            return _make_debug_party()
        return members

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(BG_COLOR)
        state = self._holder.get()
        members = self._get_members(state)

        self._draw_header(screen, state.repository.gp)

        row_y = PAD_Y + HEADER_H
        for i, member in enumerate(members):
            self._draw_row(screen, member, i, row_y, selected=(i == self._selected))
            row_y += ROW_H + ROW_GAP

        self._draw_footer(screen)

    # ── Header ────────────────────────────────────────────────

    def _draw_header(self, screen: pygame.Surface, gp: int) -> None:
        title = self._font_title.render("STATUS", True, HEADER_COLOR)
        screen.blit(title, (PAD_X, PAD_Y))

        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gp_val   = self._font_gp.render(f"{gp:,}", True, TEXT_PRIMARY)
        gx = Settings.SCREEN_WIDTH - PAD_X - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD_Y + 2))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD_Y + 2))

        pygame.draw.line(
            screen, (68, 68, 68),
            (PAD_X, PAD_Y + HEADER_H - 4),
            (Settings.SCREEN_WIDTH - PAD_X, PAD_Y + HEADER_H - 4),
        )

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

        if selected:
            cur = self._font_stat.render("▶", True, HEADER_COLOR)
            screen.blit(cur, (PAD_X + 6, y + ROW_H // 2 - cur.get_height() // 2))

        x = PAD_X + COL_GUTTER
        x = self._draw_col_name(screen, member, x, y)
        x = self._draw_col_exp(screen, member, x, y)
        x = self._draw_col_hpmp(screen, member, x, y)
        x = self._draw_col_stats(screen, member, x, y)
        self._draw_col_gear(screen, member, x, y)

    # ── Columns ───────────────────────────────────────────────

    def _draw_col_name(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        # Portrait box — centered vertically in row
        port_y = y + (ROW_H - PORTRAIT_SIZE) // 2
        port_rect = (x, port_y, PORTRAIT_SIZE, PORTRAIT_SIZE)
        pygame.draw.rect(screen, (50, 50, 80), port_rect, border_radius=4)
        pygame.draw.rect(screen, (90, 90, 130), port_rect, 1, border_radius=4)

        initials = "".join(w[0].upper() for w in m.name.split()[:2])
        init_surf = self._font_stat.render(initials, True, TEXT_SECONDARY)
        screen.blit(init_surf, (
            port_rect[0] + PORTRAIT_SIZE // 2 - init_surf.get_width() // 2,
            port_rect[1] + PORTRAIT_SIZE // 2 - init_surf.get_height() // 2,
        ))

        # Name + class — vertically centered beside portrait
        tx = x + PORTRAIT_SIZE + 10
        content_h = self._font_name.get_height() + 6 + self._font_class.get_height()
        ty = y + (ROW_H - content_h) // 2

        name_surf = self._font_name.render(m.name, True, TEXT_PRIMARY)
        screen.blit(name_surf, (tx, ty))

        cls_surf = self._font_class.render(m.class_name, True, TEXT_SECONDARY)
        screen.blit(cls_surf, (tx, ty + self._font_name.get_height() + 4))

        return x + COL_NAME_W + 50

    def _draw_col_exp(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        pct = m.exp_pct
        bar_w = COL_EXP_W

        line_h = self._font_stat.get_height()
        content_h = line_h + 4 + line_h + 6 + BAR_H
        cy = y + (ROW_H - content_h) // 2

        # Level
        lv_surf = self._font_stat.render(f"Lv {m.level}", True, TEXT_PRIMARY)
        screen.blit(lv_surf, (x, cy))

        # EXP bar
        bar_y = cy + line_h + 4
        pygame.draw.rect(screen, (17, 17, 46), (x, bar_y, bar_w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, EXP_BAR, (x, bar_y, int(bar_w * pct), BAR_H), border_radius=3)

        # EXP / next
        exp_str = f"{m.exp}/{m.exp_next}"
        exp_surf = self._font_stat.render(exp_str, True, TEXT_SECONDARY)
        screen.blit(exp_surf, (x, cy + line_h + 15))

        return x + COL_EXP_W + 12

    def _draw_col_hpmp(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        bar_w = 100
        lbl_w = 28

        # Two bars + labels: HP block + gap + MP block
        line_h = self._font_stat.get_height()
        block_h = line_h + 4 + BAR_H
        gap = 10
        total_h = block_h * 2 + gap
        cy = y + (ROW_H - total_h) // 2

        # ── HP ────────────────────────────────────────────────
        hp_pct  = m.hp / m.hp_max if m.hp_max > 0 else 0
        low_hp  = hp_pct < HP_LOW_THRESHOLD
        hp_col  = HP_BAR_LOW if low_hp else HP_BAR_OK
        hp_tcol = HP_TEXT_LOW if low_hp else TEXT_SECONDARY

        hp_lbl = self._font_stat.render("HP", True, (122, 170, 122))
        screen.blit(hp_lbl, (x, cy))

        hp_val = self._font_stat.render(f"{m.hp}/{m.hp_max}", True, hp_tcol)
        screen.blit(hp_val, (x + lbl_w + bar_w + 10, cy))

        bar_y = cy + 4
        pygame.draw.rect(screen, (17, 17, 46), (x + lbl_w + 5, bar_y, bar_w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, hp_col,       (x + lbl_w + 5, bar_y, int(bar_w * hp_pct), BAR_H), border_radius=3)

        # ── MP ────────────────────────────────────────────────
        mp_y = cy + block_h + gap

        if m.mp_max > 0:
            mp_pct = m.mp / m.mp_max
            mp_lbl = self._font_stat.render("MP", True, (122, 122, 238))
            screen.blit(mp_lbl, (x, mp_y))

            mp_val = self._font_stat.render(f"{m.mp}/{m.mp_max}", True, TEXT_SECONDARY)
            screen.blit(mp_val, (x + lbl_w + bar_w + 10, mp_y))

            mp_bar_y = mp_y + 4
            pygame.draw.rect(screen, (17, 17, 46), (x + lbl_w + 5, mp_bar_y, bar_w, BAR_H), border_radius=3)
            pygame.draw.rect(screen, MP_BAR,       (x + lbl_w + 5, mp_bar_y, int(bar_w * mp_pct), BAR_H), border_radius=3)
        else:
            mp_lbl = self._font_stat.render("MP", True, TEXT_DIM)
            screen.blit(mp_lbl, (x, mp_y))
            mp_dash = self._font_stat.render("—", True, TEXT_DIM)
            screen.blit(mp_dash, (x + lbl_w + 4, mp_y))

        return x + COL_HPMP_W + 25

    def _draw_col_stats(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> int:
        lines = [
            ("STR", f"{m.str_}"),
            ("DEX", f"{m.dex}"),
            ("CON", f"{m.con}"),
            ("INT", f"{m.int_}"),
        ]
        line_h = self._font_stat.get_height() + 6
        total_h = len(lines) * line_h
        cy = y + (ROW_H - total_h) // 2
        col2_x = x + 38

        for i, (label, val) in enumerate(lines):
            row_y = cy + i * line_h
            lbl_s = self._font_stat.render(label, True, TEXT_SECONDARY)
            val_s = self._font_stat.render(val,   True, TEXT_PRIMARY)
            screen.blit(lbl_s, (x,      row_y))
            screen.blit(val_s, (col2_x, row_y))

        return x + COL_STATS_W + 12

    def _draw_col_gear(self, screen: pygame.Surface, m: MemberState, x: int, y: int) -> None:
        # Order: Helm, Body, Weapon, Shield, Acc
        slots = [
            ("Helm",   m.equipped.get("helmet",    "")),
            ("Body",   m.equipped.get("body",      "")),
            ("Wpn",    m.equipped.get("weapon",    "")),
            ("Shld",   m.equipped.get("shield",    "")),
            ("Acc",    m.equipped.get("accessory", "")),
        ]

        line_h = self._font_stat.get_height() + 5
        total_h = len(slots) * line_h
        cy = y + (ROW_H - total_h) // 2

        lbl_w = 50

        for i, (lbl, val) in enumerate(slots):
            ry = cy + i * line_h
            lbl_s = self._font_stat.render(lbl, True, MUTED)
            val_s = self._font_stat.render(val or "—", True, TEXT_SECONDARY if val else TEXT_DIM)
            screen.blit(lbl_s, (x, ry))
            screen.blit(val_s, (x + lbl_w, ry))

    # ── Footer ────────────────────────────────────────────────

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = Settings.SCREEN_HEIGHT - FOOTER_H
        pygame.draw.line(screen, (51, 51, 51),
                         (PAD_X, fy), (Settings.SCREEN_WIDTH - PAD_X, fy))
        hint = self._font_hint.render("↑↓ select · ENTER detail · S close", True, MUTED)
        screen.blit(hint, (PAD_X, fy + 8))
