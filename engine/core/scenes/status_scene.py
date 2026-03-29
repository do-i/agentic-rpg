# engine/core/scenes/status_scene.py

from __future__ import annotations

from pathlib import Path
import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.party_state import MemberState

# ── Colors ────────────────────────────────────────────────────
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


class StatusScene(Scene):
    """
    Full-screen party status overview.
    Reads directly from GameState.party — no hardcoded data.
    S / ESC to close.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str = "",
        return_scene_name: str = "world_map",
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._return_scene_name = return_scene_name
        self._scenario_path = scenario_path
        self._selected = 0
        self._fonts_ready = False
        self._portraits: dict[str, pygame.Surface] = {}

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
        self._font_title = pygame.font.SysFont("Arial", 20, bold=True)
        self._font_name  = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_class = pygame.font.SysFont("Arial", 15)
        self._font_level = pygame.font.SysFont("Arial", 15)
        self._font_stat  = pygame.font.SysFont("Arial", 14)
        self._font_hint  = pygame.font.SysFont("Arial", 14)
        self._font_gp    = pygame.font.SysFont("Arial", 17)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        members = self._holder.get().party.members
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_s, pygame.K_ESCAPE):
                self._scene_manager.switch(self._registry.get(self._return_scene_name))
            elif event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(members) - 1, self._selected + 1)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(BG_COLOR)
        state   = self._holder.get()
        members = state.party.members

        self._draw_header(screen, state.repository.gp)

        if not members:
            s = self._font_stat.render("No party members.", True, TEXT_DIM)
            screen.blit(s, (PAD_X, PAD_Y + HEADER_H + 8))
            self._draw_footer(screen)
            return

        row_y = PAD_Y + HEADER_H
        for i, member in enumerate(members):
            self._draw_row(screen, member, i, row_y, selected=(i == self._selected))
            row_y += ROW_H + ROW_GAP

        self._draw_footer(screen)

    def _draw_header(self, screen: pygame.Surface, gp: int) -> None:
        screen.blit(self._font_title.render("STATUS", True, HEADER_COLOR), (PAD_X, PAD_Y))
        gp_val   = self._font_gp.render(f"{gp:,}", True, TEXT_PRIMARY)
        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gx = Settings.SCREEN_WIDTH - PAD_X - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD_Y + 2))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD_Y + 2))
        pygame.draw.line(screen, (68, 68, 68),
                         (PAD_X, PAD_Y + HEADER_H - 4),
                         (Settings.SCREEN_WIDTH - PAD_X, PAD_Y + HEADER_H - 4))

    def _draw_row(self, screen, m: MemberState, index: int, y: int, selected: bool) -> None:
        row_w = Settings.SCREEN_WIDTH - PAD_X * 2
        bg  = ROW_COLOR_SEL if selected else ROW_COLOR_NORM
        bdr = BORDER_SEL    if selected else BORDER_NORM
        pygame.draw.rect(screen, bg,  (PAD_X, y, row_w, ROW_H), border_radius=4)
        pygame.draw.rect(screen, bdr, (PAD_X, y, row_w, ROW_H), 1, border_radius=4)

        if selected:
            cur = self._font_stat.render("▶", True, HEADER_COLOR)
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
                         (x, bar_y, int(bar_w * m.exp_pct), BAR_H), border_radius=3)
        screen.blit(self._font_stat.render(f"{m.exp}/{m.exp_next}", True, TEXT_SECONDARY),
                    (x, cy + line_h + 25))
        return x + COL_EXP_W + 12

    def _draw_hpmp(self, screen, m: MemberState, x: int, y: int) -> int:
        bar_w  = 100
        lbl_w  = 28
        line_h = self._font_stat.get_height()
        block_h = line_h + 4 + BAR_H
        cy = y + (ROW_H - block_h * 2 - 10) // 2

        # HP
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

        # MP
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
            screen.blit(self._font_stat.render("—", True, TEXT_DIM), (x + lbl_w + 4, mp_y))

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
                val or "—", True, TEXT_SECONDARY if val else TEXT_DIM), (x + 50, ry))

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = Settings.SCREEN_HEIGHT - FOOTER_H
        pygame.draw.line(screen, (51, 51, 51),
                         (PAD_X, fy), (Settings.SCREEN_WIDTH - PAD_X, fy))
        hint = self._font_hint.render("↑↓ select · S close", True, MUTED)
        screen.blit(hint, (PAD_X, fy + 8))
