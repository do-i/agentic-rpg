# engine/battle/post_battle_scene.py
#
# Victory / spoils screen shown after a won battle. Restyled to match the
# field-menu screens (Status / Equip / Spell): themed backdrop, accent header,
# bordered panels, and the shared INK/GOLD/MUTED palette via field_menu_theme.
#
# Layout:
#   Header              — "VICTORY" + total EXP earned subtitle.
#   Party panel (left)  — one growth card per member: portrait, name/level,
#                         EXP share, and a LEVEL UP badge with HP/MP gains.
#   Spoils panel (right)— GP, magic cores, and item drops.
#
# The EXP "tally" animates on entry; pressing confirm skips it, then a second
# press continues to the world map (behaviour unchanged from before).

from __future__ import annotations

import pygame

from engine.common.scene.scene import Scene
from engine.common.font_provider import get_fonts
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.battle.battle_rewards import BattleRewards
from engine.common.color_constants import C_TEXT_DIM
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    TEAL,
    VIOLET,
    draw_divider,
    fit_text,
    icon_surface,
    member_icon_path,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    render_row_frame,
)

PAD_X = 40
PAD_Y = 30
GAP = 18
LOOT_ROW_H = 54

HP_GAIN = (132, 196, 111)
MP_GAIN = TEAL


class PostBattleScene(Scene):
    """
    Displays EXP gained, level-ups, and loot after a victorious battle.
    Player presses SPACE / ENTER / Z to continue → world map.
    """

    def __init__(
        self,
        rewards: BattleRewards,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_continue: callable,
        sfx_manager,
    ) -> None:
        self._rewards = rewards
        self._scene_manager = scene_manager
        self._registry = registry
        self._on_continue = on_continue
        self._sfx_manager = sfx_manager
        self._fonts_ready = False

        # animate the EXP tally on entry
        self._exp_fill: float = 0.0      # 0.0 → 1.0
        self._exp_done: bool = False
        self._ready_to_exit: bool = False

    # ── Font init ─────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_stat  = f.get(16)
        self._font_meta  = f.get(14)
        self._font_hint  = f.get(14)
        self._font_small = f.get(13)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                              pygame.K_KP_ENTER, pygame.K_z):
                self._sfx_manager.play("confirm")
                if not self._exp_done:
                    # skip animation
                    self._exp_fill = 1.0
                    self._exp_done = True
                    self._ready_to_exit = True
                elif self._ready_to_exit:
                    self._on_continue()

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if not self._exp_done:
            self._exp_fill = min(1.0, self._exp_fill + delta * 0.6)
            if self._exp_fill >= 1.0:
                self._exp_done = True
                self._ready_to_exit = True

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)
        total = int(round(self._rewards.total_exp * self._exp_fill))
        render_header(
            screen, self._font_title, self._font_hint,
            "VICTORY", f"{total} EXP earned", PAD_X, PAD_Y,
        )

        party_rect, spoils_rect = self._layout(screen)
        render_panel(screen, party_rect, active=True,
                     title="Party", title_font=self._font_head)
        self._render_party(screen, party_rect)

        render_panel(screen, spoils_rect, active=False,
                     title="Spoils", title_font=self._font_head)
        self._render_spoils(screen, spoils_rect)

        self._render_hint(screen)

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        panel_h = max(360, sh - top - 62)
        available = sw - PAD_X * 2 - GAP
        spoils_w = min(360, max(300, int(sw * 0.30)))
        party_w = available - spoils_w
        party_rect = pygame.Rect(PAD_X, top, party_w, panel_h)
        spoils_rect = pygame.Rect(party_rect.right + GAP, top, spoils_w, panel_h)
        return party_rect, spoils_rect

    # ── Party growth cards ────────────────────────────────────

    def _render_party(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        results = self._rewards.member_results
        x = panel.x + 16
        top = panel.y + 52
        w = panel.w - 32
        if not results:
            screen.blit(self._font_row.render("No survivors.", True, DIM), (x, top))
            return

        n = len(results)
        gap = 14
        avail = (panel.bottom - 16) - top
        row_h = min(118, (avail - gap * (n - 1)) // n)
        portrait = min(row_h - 16, 92)

        for i, result in enumerate(results):
            row = pygame.Rect(x, top + i * (row_h + gap), w, row_h)
            self._render_growth_card(screen, row, result, portrait)

    def _render_growth_card(
        self, screen: pygame.Surface, rect: pygame.Rect, result, portrait: int,
    ) -> None:
        leveled = bool(result.level_ups)
        ko = result.exp_gained == 0
        render_row_frame(screen, rect, focused=leveled, dimmed_sel=False)

        icon = icon_surface(
            f"member_{result.member_id}", portrait,
            dimmed=ko, image_path=member_icon_path(result.member_id),
        )
        screen.blit(icon, (rect.x + 12, rect.y + (rect.h - portrait) // 2))

        tx = rect.x + 24 + portrait
        max_w = rect.right - tx - 14
        name_col = DIM if ko else INK
        name = fit_text(
            self._font_head,
            result.member_name + ("  [KO]" if ko else ""),
            name_col, max_w,
        )

        # animated EXP share
        shown = int(round(result.exp_gained * self._exp_fill))
        exp_txt = f"+{shown} EXP" if result.exp_gained else "-"
        exp = self._font_meta.render(exp_txt, True, DIM if ko else MUTED)

        if leveled:
            lu = result.level_ups[-1]
            lvl = fit_text(
                self._font_row, f"LEVEL UP   {lu.old_level} → {lu.new_level}",
                GOLD, max_w,
            )
            gains = self._render_gains(lu)
            line_gap = 6
            block_h = (name.get_height() + line_gap + lvl.get_height()
                       + line_gap + gains.get_height() + line_gap + exp.get_height())
            ty = rect.y + (rect.h - block_h) // 2
            screen.blit(name, (tx, ty)); ty += name.get_height() + line_gap
            screen.blit(lvl, (tx, ty)); ty += lvl.get_height() + line_gap
            screen.blit(gains, (tx, ty)); ty += gains.get_height() + line_gap
            screen.blit(exp, (tx, ty))
        else:
            line_gap = 8
            block_h = name.get_height() + line_gap + exp.get_height()
            ty = rect.y + (rect.h - block_h) // 2
            screen.blit(name, (tx, ty)); ty += name.get_height() + line_gap
            screen.blit(exp, (tx, ty))

    def _render_gains(self, lu) -> pygame.Surface:
        """Render the HP/MP/stat gains for a level-up onto one surface."""
        parts = [
            (f"HP +{lu.hp_gained}", HP_GAIN),
            (f"MP +{lu.mp_gained}", MP_GAIN),
        ]
        for label, val in (
            ("STR", lu.str_gained), ("DEX", lu.dex_gained),
            ("CON", lu.con_gained), ("INT", lu.int_gained),
        ):
            if val:
                parts.append((f"{label} +{val}", VIOLET))

        gap = 16
        surfs = [(self._font_meta.render(t, True, c), c) for t, c in parts]
        width = sum(s.get_width() for s, _ in surfs) + gap * (len(surfs) - 1)
        height = max(s.get_height() for s, _ in surfs)
        out = pygame.Surface((max(1, width), height), pygame.SRCALPHA)
        cx = 0
        for s, _ in surfs:
            out.blit(s, (cx, 0))
            cx += s.get_width() + gap
        return out

    # ── Spoils ────────────────────────────────────────────────

    def _render_spoils(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        loot = self._rewards.loot
        x = panel.x + 16
        y = panel.y + 52
        w = panel.w - 32

        if loot.gp_gained:
            screen.blit(self._font_stat.render("GP", True, MUTED), (x, y))
            gp = self._font_stat.render(f"+{loot.gp_gained}", True, GOLD)
            screen.blit(gp, (panel.right - 16 - gp.get_width(), y))
            y += self._font_stat.get_height() + 8
            draw_divider(screen, x, y, w)
            y += 12

        rows: list[tuple[str, str, str]] = []
        for mc in loot.mc_drops:
            rows.append((f"mc_{mc['size']}", f"Magic Core ({mc['size']})", f"x{mc['qty']}"))
        for item in loot.item_drops:
            rows.append((f"item_{item.get('id', item['name'])}",
                         item["name"], f"x{item.get('qty', 1)}"))

        if not rows:
            screen.blit(self._font_row.render("No loot.", True, DIM), (x, y))
            return

        for icon_key, label, qty in rows:
            rect = pygame.Rect(x, y, w, LOOT_ROW_H)
            render_icon_row(
                screen, self._font_row, rect, label,
                icon_key=icon_key,
                focused=False,
                dimmed_sel=False,
                color=INK,
                right_text=qty,
                right_font=self._font_meta,
            )
            y += LOOT_ROW_H + 8

    # ── Hint ──────────────────────────────────────────────────

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        if not self._ready_to_exit:
            return
        text = "SPACE / ENTER  continue"
        hint = self._font_hint.render(text, True, C_TEXT_DIM)
        alpha = 128 + int(127 * abs((pygame.time.get_ticks() % 1000) / 500.0 - 1.0))
        hint.set_alpha(alpha)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))
