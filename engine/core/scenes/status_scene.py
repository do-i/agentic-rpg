# engine/core/scenes/status_scene.py

from __future__ import annotations

from pathlib import Path
import pygame
import yaml
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.party_state import MemberState
from engine.core.scenes.target_select_overlay import TargetSelectOverlay

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

C_SPELL_BG      = (22, 22, 44)
C_SPELL_BDR     = (120, 110, 180)
C_SPELL_SEL     = (45, 42, 75)
C_SPELL_DIS     = (70, 70, 80)
C_MP_COST       = (130, 130, 220)
C_TOAST         = (100, 220, 130)
C_WARN          = (220, 180, 80)

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

# field-usable spell types (no offensive spells on world map)
FIELD_SPELL_TYPES = {"heal", "utility", "buff"}

TOAST_DUR = 1.2


def _load_class_data(classes_dir: Path, class_name: str) -> dict:
    path = classes_dir / f"{class_name}.yaml"
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)


class StatusScene(Scene):
    """
    Full-screen party status overview.
    Reads directly from GameState.party — no hardcoded data.
    S / ESC to close.  ENTER to open spell list for selected member.
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

        # spell sub-menu state
        self._spell_list: list[dict] | None = None   # visible spell menu
        self._spell_sel: int = 0
        self._spell_caster: MemberState | None = None
        self._target_overlay: TargetSelectOverlay | None = None
        self._toast_text: str = ""
        self._toast_timer: float = 0.0

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
        self._font_spell = pygame.font.SysFont("Arial", 15)
        self._font_spell_title = pygame.font.SysFont("Arial", 16, bold=True)
        self._font_toast = pygame.font.SysFont("Arial", 18, bold=True)
        self._fonts_ready = True

    # ── Spell helpers ─────────────────────────────────────────

    def _field_spells(self, member: MemberState) -> list[dict]:
        """Load available field-usable spells for this member."""
        classes_dir = Path(self._scenario_path) / "data" / "classes"
        class_data = _load_class_data(classes_dir, member.class_name)
        abilities = class_data.get("abilities", [])
        result = []
        for ab in abilities:
            if ab.get("type") not in FIELD_SPELL_TYPES:
                continue
            if ab.get("unlock_level", 1) > member.level:
                continue
            result.append(ab)
        return result

    def _valid_targets(self, spell: dict) -> list[MemberState]:
        members = self._holder.get().party.members
        target = spell.get("target", "single_ally")
        if target == "single_ko":
            return [m for m in members if m.hp <= 0]
        if spell.get("revive_hp_pct"):
            return [m for m in members if m.hp <= 0]
        return [m for m in members if m.hp > 0]

    def _apply_spell(self, spell: dict, caster: MemberState, target: MemberState) -> str:
        """Apply spell effect. Returns result message."""
        caster.mp = max(0, caster.mp - spell.get("mp_cost", 0))
        spell_type = spell.get("type")

        if spell_type == "heal":
            if spell.get("revive_hp_pct"):
                pct = spell["revive_hp_pct"]
                target.hp = max(1, int(target.hp_max * pct))
                return f"{target.name} revived!"
            coeff = spell.get("heal_coeff", 1.0)
            amount = int(caster.int_ * coeff)
            before = target.hp
            target.hp = min(target.hp_max, target.hp + amount)
            healed = target.hp - before
            return f"{target.name} healed {healed} HP!"

        if spell_type == "utility":
            return f"{target.name} cured!"

        if spell_type == "buff":
            return f"{spell['name']} cast!"

        return f"{spell['name']} used!"

    def _apply_spell_all(self, spell: dict, caster: MemberState) -> str:
        """Apply AoE heal to all alive members."""
        caster.mp = max(0, caster.mp - spell.get("mp_cost", 0))
        coeff = spell.get("heal_coeff", 1.0)
        amount = int(caster.int_ * coeff)
        members = self._holder.get().party.members
        total = 0
        for m in members:
            if m.hp <= 0:
                continue
            before = m.hp
            m.hp = min(m.hp_max, m.hp + amount)
            total += m.hp - before
        return f"Party healed {total} HP!"

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return

        if self._toast_timer > 0:
            return

        members = self._holder.get().party.members
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self._spell_list is not None:
                self._handle_spell_key(event.key)
                return

            if event.key in (pygame.K_s, pygame.K_ESCAPE):
                self._scene_manager.switch(self._registry.get(self._return_scene_name))
            elif event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(members) - 1, self._selected + 1)
            elif event.key == pygame.K_RETURN:
                self._open_spell_menu()

    def _open_spell_menu(self) -> None:
        members = self._holder.get().party.members
        if not members:
            return
        member = members[self._selected]
        spells = self._field_spells(member)
        if not spells:
            self._toast_text = f"{member.name} has no field spells."
            self._toast_timer = TOAST_DUR
            return
        self._spell_caster = member
        self._spell_list = spells
        self._spell_sel = 0

    def _handle_spell_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._spell_list = None
            self._spell_caster = None
            return

        spells = self._spell_list
        if key == pygame.K_UP:
            self._spell_sel = max(0, self._spell_sel - 1)
        elif key == pygame.K_DOWN:
            self._spell_sel = min(len(spells) - 1, self._spell_sel + 1)
        elif key == pygame.K_RETURN:
            spell = spells[self._spell_sel]
            cost = spell.get("mp_cost", 0)
            if cost > self._spell_caster.mp:
                return  # not enough MP
            target_type = spell.get("target", "single_ally")
            if target_type in ("all_allies", "party"):
                msg = self._apply_spell_all(spell, self._spell_caster)
                self._spell_list = None
                self._toast_text = msg
                self._toast_timer = TOAST_DUR
            else:
                targets = self._valid_targets(spell)
                if not targets:
                    self._toast_text = "No valid targets."
                    self._toast_timer = TOAST_DUR
                    self._spell_list = None
                    return
                pending_spell = spell
                caster = self._spell_caster
                self._target_overlay = TargetSelectOverlay(
                    targets=targets,
                    item_label=spell["name"],
                    on_confirm=lambda t, s=pending_spell, c=caster: self._on_target_confirm(s, c, t),
                    on_cancel=self._on_target_cancel,
                )

    def _on_target_confirm(self, spell: dict, caster: MemberState, target: MemberState) -> None:
        msg = self._apply_spell(spell, caster, target)
        self._target_overlay = None
        self._spell_list = None
        self._spell_caster = None
        self._toast_text = msg
        self._toast_timer = TOAST_DUR

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._toast_timer > 0:
            self._toast_timer -= delta

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

        if self._spell_list is not None:
            self._draw_spell_menu(screen)
        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._toast_timer > 0:
            self._draw_toast(screen)

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

    # ── Spell menu overlay ────────────────────────────────────

    def _draw_spell_menu(self, screen: pygame.Surface) -> None:
        spells = self._spell_list
        caster = self._spell_caster
        if not spells or not caster:
            return

        row_h  = 32
        pad    = 16
        w      = 340
        h      = pad + 28 + len(spells) * row_h + pad + 20
        x      = (Settings.SCREEN_WIDTH - w) // 2
        y      = (Settings.SCREEN_HEIGHT - h) // 2

        # dim
        overlay = pygame.Surface(
            (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # box
        pygame.draw.rect(screen, C_SPELL_BG,  (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, C_SPELL_BDR, (x, y, w, h), 2, border_radius=6)

        # title
        title = self._font_spell_title.render(f"{caster.name} — Spells", True, HEADER_COLOR)
        screen.blit(title, (x + pad, y + pad))

        # MP display
        mp_s = self._font_spell.render(f"MP {caster.mp}/{caster.mp_max}", True, C_MP_COST)
        screen.blit(mp_s, (x + w - mp_s.get_width() - pad, y + pad))

        # rows
        ry = y + pad + 28
        for i, spell in enumerate(spells):
            sel      = (i == self._spell_sel)
            cost     = spell.get("mp_cost", 0)
            disabled = cost > caster.mp

            if sel:
                pygame.draw.rect(screen, C_SPELL_SEL, (x + 4, ry, w - 8, row_h), border_radius=3)
                cur = self._font_spell.render("▶", True, HEADER_COLOR)
                screen.blit(cur, (x + 10, ry + (row_h - cur.get_height()) // 2))

            name_c = C_SPELL_DIS if disabled else (TEXT_PRIMARY if sel else TEXT_SECONDARY)
            name_s = self._font_spell.render(spell["name"], True, name_c)
            screen.blit(name_s, (x + 28, ry + (row_h - name_s.get_height()) // 2))

            cost_c = C_SPELL_DIS if disabled else C_MP_COST
            cost_s = self._font_spell.render(f"{cost} MP", True, cost_c)
            screen.blit(cost_s, (x + w - cost_s.get_width() - pad,
                                  ry + (row_h - cost_s.get_height()) // 2))
            ry += row_h

        # hint
        hint = self._font_hint.render("ENTER cast · ESC back", True, MUTED)
        screen.blit(hint, (x + pad, y + h - pad - hint.get_height() + 4))

    # ── Toast ─────────────────────────────────────────────────

    def _draw_toast(self, screen: pygame.Surface) -> None:
        surf = self._font_toast.render(self._toast_text, True, C_TOAST)
        tw, th = surf.get_size()
        tx = (Settings.SCREEN_WIDTH - tw) // 2
        ty = Settings.SCREEN_HEIGHT - 60
        bg = pygame.Surface((tw + 24, th + 12), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        screen.blit(bg, (tx - 12, ty - 6))
        screen.blit(surf, (tx, ty))

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = Settings.SCREEN_HEIGHT - FOOTER_H
        pygame.draw.line(screen, (51, 51, 51),
                         (PAD_X, fy), (Settings.SCREEN_WIDTH - PAD_X, fy))
        hint = self._font_hint.render("↑↓ select · ENTER spells · S close", True, MUTED)
        screen.blit(hint, (PAD_X, fy + 8))
