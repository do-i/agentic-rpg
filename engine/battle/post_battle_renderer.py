# engine/battle/post_battle_renderer.py
#
# Drawing for the victory / spoils screen — party growth cards, spoils
# list, level-up modal, hints. PostBattleScene owns flow (tally
# animation, modal sequencing) and passes a per-frame view here.
#
# Note: the scenario font (Philosopher) has no "→" glyph — it renders as a
# tofu box. All on-screen arrows use ASCII "->" (matching the equip screen).

from __future__ import annotations

import pygame

from engine.battle.battle_rewards import BattleRewards
from engine.common.color_constants import C_TEXT_DIM
from engine.common.font_provider import FontSet
from engine.common.font_roles import CAPTION
from engine.common.ui.chrome import (
    draw_divider,
    fit_text,
    icon_surface,
    render_backdrop,
    render_header,
    render_icon_row,
    render_modal,
    render_panel,
    render_row_frame,
)
from engine.common.ui.theme import DIM, GOLD, INK, MUTED, member_icon_path

PAD_X = 40
PAD_Y = 30
GAP = 18
LOOT_ROW_H = 54

# Colour for a positive stat delta in the level-up modal.
GAIN = (132, 196, 111)


class PostBattleRenderer:
    def __init__(self, rewards: BattleRewards) -> None:
        self._rewards = rewards
        self._fonts = FontSet(
            title=(24, True), head=(18, True), row=18, stat=16,
            meta=CAPTION, hint=14, small=CAPTION,
        )

    # ── Main entry point ──────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        *,
        shown_map: dict[str, int],
        lu_active: bool,
        lu_entry: dict | None,
        lu_index: int,
        lu_total: int,
        ready_to_exit: bool,
    ) -> None:
        render_backdrop(screen)

        # The EXP pool is paid out to each member via shown_map; the total is
        # intentionally not surfaced in the header.
        render_header(
            screen, self._fonts.title, self._fonts.hint,
            "VICTORY", "", PAD_X, PAD_Y,
        )

        party_rect, spoils_rect = self._layout(screen)
        render_panel(screen, party_rect, active=True,
                     title="Party", title_font=self._fonts.head)
        self._render_party(screen, party_rect, shown_map)

        render_panel(screen, spoils_rect, active=False,
                     title="Spoils", title_font=self._fonts.head)
        self._render_spoils(screen, spoils_rect)

        if lu_active and lu_entry is not None:
            self._render_levelup_modal(screen, lu_entry, lu_index, lu_total)
        else:
            self._render_hint(screen, ready_to_exit)

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

    def _render_party(
        self, screen: pygame.Surface, panel: pygame.Rect, shown_map: dict[str, int],
    ) -> None:
        results = self._rewards.member_results
        x = panel.x + 16
        top = panel.y + 52
        w = panel.w - 32
        if not results:
            screen.blit(self._fonts.row.render("No survivors.", True, DIM), (x, top))
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
            self._fonts.head,
            result.member_name + ("  [KO]" if ko else ""),
            name_col, max_w,
        )

        # animated EXP share (driven by the sequential pay-out tally)
        exp_txt = f"+{shown} EXP" if result.exp_gained else "-"
        exp = self._fonts.meta.render(exp_txt, True, DIM if ko else MUTED)

        if leveled:
            old_level = result.level_ups[0].old_level
            new_level = result.level_ups[-1].new_level
            lvl = fit_text(
                self._fonts.row, f"LEVEL UP!   Lv {old_level} -> {new_level}",
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

    def _render_levelup_modal(
        self, screen: pygame.Surface, s: dict, index: int, total: int,
    ) -> None:
        rect = render_modal(screen, 540, 432, title="LEVEL UP",
                            title_font=self._fonts.head)

        # ── Portrait + name + new level ───────────────────────
        portrait = 88
        px, py = rect.x + 28, rect.y + 58
        icon = icon_surface(
            f"member_{s['member_id']}", portrait,
            image_path=member_icon_path(s["member_id"]),
        )
        screen.blit(icon, (px, py))

        tx = px + portrait + 22
        name = self._fonts.title.render(s["member_name"], True, INK)
        screen.blit(name, (tx, py + 8))
        lvl = self._fonts.row.render(
            f"Lv {s['old_level']} -> {s['new_level']}", True, GOLD)
        screen.blit(lvl, (tx, py + 8 + name.get_height() + 8))

        # page indicator when more than one member grew
        if total > 1:
            idx = self._fonts.meta.render(f"{index + 1} / {total}", True, MUTED)
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
            screen.blit(self._fonts.stat.render(label, True, MUTED), (col_label, dy))
            self._blit_right(screen, self._fonts.stat, str(before), DIM, col_before, dy)
            screen.blit(self._fonts.stat.render("->", True, MUTED), (col_arrow, dy))
            self._blit_right(screen, self._fonts.stat, str(after), INK, col_after + 46, dy)
            if gain > 0:
                screen.blit(self._fonts.meta.render(f"+{gain}", True, GAIN), (col_gain, dy))
            dy += self._fonts.stat.get_height() + 10

        # ── Hint ──────────────────────────────────────────────
        last_modal = index >= total - 1
        text = "ENTER  continue" if last_modal else "ENTER  next"
        hint = self._fonts.hint.render(text, True, C_TEXT_DIM)
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
            screen.blit(self._fonts.stat.render("GP", True, MUTED), (x, y))
            gp = self._fonts.stat.render(f"+{loot.gp_gained}", True, GOLD)
            screen.blit(gp, (panel.right - 16 - gp.get_width(), y))
            y += self._fonts.stat.get_height() + 8
            draw_divider(screen, x, y, w)
            y += 12

        rows: list[tuple[str, str, str]] = []
        for mc in loot.mc_drops:
            rows.append((f"mc_{mc['size']}", f"Magic Core ({mc['size']})", f"x{mc['qty']}"))
        for item in loot.item_drops:
            rows.append((f"item_{item.get('id', item['name'])}",
                         item["name"], f"x{item.get('qty', 1)}"))

        if not rows:
            screen.blit(self._fonts.row.render("No loot.", True, DIM), (x, y))
            return

        for icon_key, label, qty in rows:
            rect = pygame.Rect(x, y, w, LOOT_ROW_H)
            render_icon_row(
                screen, self._fonts.row, rect, label,
                icon_key=icon_key,
                focused=False,
                dimmed_sel=False,
                color=INK,
                right_text=qty,
                right_font=self._fonts.meta,
            )
            y += LOOT_ROW_H + 8

    # ── Hint ──────────────────────────────────────────────────

    def _render_hint(self, screen: pygame.Surface, ready_to_exit: bool) -> None:
        sw, sh = screen.get_size()
        if not ready_to_exit:
            return
        text = "SPACE / ENTER  continue"
        hint = self._fonts.hint.render(text, True, C_TEXT_DIM)
        alpha = 128 + int(127 * abs((pygame.time.get_ticks() % 1000) / 500.0 - 1.0))
        hint.set_alpha(alpha)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))
