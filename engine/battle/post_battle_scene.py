# engine/battle/post_battle_scene.py
#
# Victory / spoils screen shown after a won battle. Restyled to match the
# field-menu screens (Status / Equip / Spell): themed backdrop, accent header,
# bordered panels, and the shared INK/GOLD/MUTED palette via field_menu_theme.
#
# Layout:
#   Header              — "VICTORY" + total EXP earned subtitle.
#   Party panel (left)  — one growth card per member: portrait, name/level,
#                         EXP share, and a compact LEVEL UP! tag.
#   Spoils panel (right)— GP, magic cores, and item drops.
#
# Flow:
#   1. The EXP "tally" animates on entry; pressing confirm skips it.
#   2. If anyone levelled up, a centered modal then steps through each grown
#      member showing the new level and a before -> after stat comparison.
#   3. A final confirm continues to the world map.
#
# Note: the scenario font (Philosopher) has no "→" glyph — it renders as a
# tofu box. All on-screen arrows use ASCII "->" (matching the equip screen).

from __future__ import annotations

import pygame

from engine.common.scene.scene import Scene
from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.battle.battle_rewards import BattleRewards
from engine.common.color_constants import C_TEXT_DIM
from engine.common.field_menu_theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    draw_divider,
    fit_text,
    icon_surface,
    member_icon_path,
    render_backdrop,
    render_header,
    render_icon_row,
    render_modal,
    render_panel,
    render_row_frame,
)

PAD_X = 40
PAD_Y = 30
GAP = 18
LOOT_ROW_H = 54

# Colour for a positive stat delta in the level-up modal.
GAIN = (132, 196, 111)


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
        self._exp_fill: float = 0.0      # 0.0 -> 1.0
        self._exp_done: bool = False
        self._ready_to_exit: bool = False

        # level-up modal sequence (shown once the tally completes)
        self._lu_queue = self._build_lu_queue()
        self._lu_index: int = 0
        self._lu_active: bool = False

    # ── Font init ─────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_stat  = f.get(16)
        self._font_meta  = f.get(CAPTION)
        self._font_hint  = f.get(14)
        self._font_small = f.get(CAPTION)
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
                    # skip the tally animation
                    self._exp_fill = 1.0
                    self._exp_done = True
                    self._on_tally_done()
                elif self._lu_active:
                    # advance through the level-up modals
                    self._lu_index += 1
                    if self._lu_index >= len(self._lu_queue):
                        self._lu_active = False
                        self._ready_to_exit = True
                elif self._ready_to_exit:
                    self._on_continue()

    def _on_tally_done(self) -> None:
        """Called once the EXP tally is full. Opens the level-up modal
        sequence if anyone grew, otherwise readies the continue prompt."""
        if self._lu_queue:
            self._lu_active = True
            self._lu_index = 0
        else:
            self._ready_to_exit = True

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if not self._exp_done:
            self._exp_fill = min(1.0, self._exp_fill + delta * 0.6)
            if self._exp_fill >= 1.0:
                self._exp_done = True
                self._on_tally_done()

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)

        # The EXP pool is paid out to each member below; the running per-member
        # shares drive that animation. The total is intentionally not surfaced
        # in the header.
        shown_map = self._exp_shown()
        render_header(
            screen, self._font_title, self._font_hint,
            "VICTORY", "", PAD_X, PAD_Y,
        )

        party_rect, spoils_rect = self._layout(screen)
        render_panel(screen, party_rect, active=True,
                     title="Party", title_font=self._font_head)
        self._render_party(screen, party_rect, shown_map)

        render_panel(screen, spoils_rect, active=False,
                     title="Spoils", title_font=self._font_head)
        self._render_spoils(screen, spoils_rect)

        if self._lu_active:
            self._render_levelup_modal(screen)
        else:
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

    # ── EXP tally ─────────────────────────────────────────────

    def _exp_shown(self) -> dict[str, int]:
        """How much EXP each member has visibly received so far.

        Members are paid out sequentially as `_exp_fill` advances 0 → 1, so the
        pool drains one member at a time. The header subtracts these from the
        total, decrementing to zero exactly when the last member is paid.
        """
        results = self._rewards.member_results
        total = sum(r.exp_gained for r in results)
        target = self._exp_fill * total      # EXP awarded across the party so far
        running = 0.0
        out: dict[str, int] = {}
        for r in results:
            take = min(float(r.exp_gained), max(0.0, target - running))
            out[r.member_id] = int(round(take))
            running += r.exp_gained
        return out

    # ── Party growth cards ────────────────────────────────────

    def _render_party(
        self, screen: pygame.Surface, panel: pygame.Rect, shown_map: dict[str, int],
    ) -> None:
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
            shown = shown_map.get(result.member_id, 0)
            self._render_growth_card(screen, row, result, portrait, shown)

    def _render_growth_card(
        self, screen: pygame.Surface, rect: pygame.Rect, result, portrait: int,
        shown: int,
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

        # animated EXP share (driven by the sequential pay-out tally)
        exp_txt = f"+{shown} EXP" if result.exp_gained else "-"
        exp = self._font_meta.render(exp_txt, True, DIM if ko else MUTED)

        if leveled:
            old_level = result.level_ups[0].old_level
            new_level = result.level_ups[-1].new_level
            lvl = fit_text(
                self._font_row, f"LEVEL UP!   Lv {old_level} -> {new_level}",
                GOLD, max_w,
            )
            line_gap = 6
            block_h = (name.get_height() + line_gap + lvl.get_height()
                       + line_gap + exp.get_height())
            ty = rect.y + (rect.h - block_h) // 2
            screen.blit(name, (tx, ty)); ty += name.get_height() + line_gap
            screen.blit(lvl, (tx, ty)); ty += lvl.get_height() + line_gap
            screen.blit(exp, (tx, ty))
        else:
            line_gap = 8
            block_h = name.get_height() + line_gap + exp.get_height()
            ty = rect.y + (rect.h - block_h) // 2
            screen.blit(name, (tx, ty)); ty += name.get_height() + line_gap
            screen.blit(exp, (tx, ty))

    # ── Level-up modal ────────────────────────────────────────

    def _build_lu_queue(self) -> list[dict]:
        """One entry per member who gained at least one level, each holding the
        new level and before -> after totals for every stat. Built once at
        construction so the modal can step through it."""
        queue: list[dict] = []
        for r in self._rewards.member_results:
            if not r.level_ups:
                continue
            last = r.level_ups[-1]
            # "before" is the post-growth total minus everything gained here.
            stats = [
                ("HP", last.hp_max, sum(lu.hp_gained for lu in r.level_ups)),
                ("MP", last.mp_max, sum(lu.mp_gained for lu in r.level_ups)),
                ("STR", last.str_total, sum(lu.str_gained for lu in r.level_ups)),
                ("DEX", last.dex_total, sum(lu.dex_gained for lu in r.level_ups)),
                ("CON", last.con_total, sum(lu.con_gained for lu in r.level_ups)),
                ("INT", last.int_total, sum(lu.int_gained for lu in r.level_ups)),
            ]
            queue.append({
                "member_id": r.member_id,
                "member_name": r.member_name,
                "old_level": r.level_ups[0].old_level,
                "new_level": last.new_level,
                "stats": [(label, total - gained, total) for label, total, gained in stats],
            })
        return queue

    def _render_levelup_modal(self, screen: pygame.Surface) -> None:
        s = self._lu_queue[self._lu_index]
        rect = render_modal(screen, 540, 432, title="LEVEL UP",
                            title_font=self._font_head)

        # ── Portrait + name + new level ───────────────────────
        portrait = 88
        px, py = rect.x + 28, rect.y + 58
        icon = icon_surface(
            f"member_{s['member_id']}", portrait,
            image_path=member_icon_path(s["member_id"]),
        )
        screen.blit(icon, (px, py))

        tx = px + portrait + 22
        name = self._font_title.render(s["member_name"], True, INK)
        screen.blit(name, (tx, py + 8))
        lvl = self._font_row.render(
            f"Lv {s['old_level']} -> {s['new_level']}", True, GOLD)
        screen.blit(lvl, (tx, py + 8 + name.get_height() + 8))

        # page indicator when more than one member grew
        if len(self._lu_queue) > 1:
            idx = self._font_meta.render(
                f"{self._lu_index + 1} / {len(self._lu_queue)}", True, MUTED)
            screen.blit(idx, (rect.right - idx.get_width() - 22, rect.y + 18))

        # ── Stat table: LABEL  before  ->  after  (+gain) ─────
        dy = py + portrait + 22
        draw_divider(screen, rect.x + 28, dy, rect.w - 56)
        dy += 18

        col_label  = rect.x + 40
        col_before = rect.x + 210
        col_arrow  = rect.x + 276
        col_after  = rect.x + 330
        col_gain   = rect.x + 420
        for label, before, after in s["stats"]:
            gain = after - before
            screen.blit(self._font_stat.render(label, True, MUTED), (col_label, dy))
            self._blit_right(screen, self._font_stat, str(before), DIM, col_before, dy)
            screen.blit(self._font_stat.render("->", True, MUTED), (col_arrow, dy))
            self._blit_right(screen, self._font_stat, str(after), INK, col_after + 46, dy)
            if gain > 0:
                screen.blit(self._font_meta.render(f"+{gain}", True, GAIN), (col_gain, dy))
            dy += self._font_stat.get_height() + 10

        # ── Hint ──────────────────────────────────────────────
        last_modal = self._lu_index >= len(self._lu_queue) - 1
        text = "ENTER  continue" if last_modal else "ENTER  next"
        hint = self._font_hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, (rect.centerx - hint.get_width() // 2, rect.bottom - 34))

    @staticmethod
    def _blit_right(screen, font, text, color, right_x, y) -> None:
        surf = font.render(text, True, color)
        screen.blit(surf, (right_x - surf.get_width(), y))

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
