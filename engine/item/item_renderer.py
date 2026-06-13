# engine/ui/item_renderer.py
#
# Item scene rendering — all drawing, fonts, layout.
# Extracted from item_scene.py to separate rendering from data logic.

from __future__ import annotations

import pygame
from engine.common.font_provider import get_fonts
from engine.common.item_selection_view import (
    ItemRow, ItemSelectionTheme, ItemSelectionView,
)
from engine.common.field_menu_theme import (
    BORDER,
    BORDER_ACTIVE,
    DIM,
    EMBER,
    GOLD,
    INK,
    MUTED as THEME_MUTED,
    ROW,
    ROW_ACTIVE,
    draw_divider,
    render_backdrop,
    render_header,
    render_hint,
    render_modal,
    render_panel,
    render_row_frame,
)
from engine.item.item_entry_state import ItemEntry
from engine.item.item_logic import TABS, actions_for, display_name
from engine.item.magic_core_catalog_state import MagicCoreCatalogState
from engine.item.item_effect_handler import ItemEffectHandler

# ── Colors (field-menu theme) ─────────────────────────────────
HEADER_COLOR    = GOLD
MUTED           = THEME_MUTED
TEXT_PRIMARY    = INK
TEXT_SECONDARY  = THEME_MUTED
TEXT_DIM        = DIM

TAB_BORDER_ACT  = BORDER_ACTIVE

BTN_TEXT        = INK
BTN_TEXT_DIS    = DIM

C_CONFIRM_TXT   = GOLD

DIVIDER         = BORDER

# ── Layout ────────────────────────────────────────────────────
PAD             = 16
HEADER_H        = 44
TAB_H           = 34
TAB_GAP         = 4
FOOTER_H        = 30

FILTER_W        = 240
LIST_W          = 480
ITEM_ROW_H      = 34
ITEM_ROW_GAP    = 4
VISIBLE_ROWS    = 15
PEEK_RATIO      = 0.70

BTN_W           = 110
BTN_H           = 34
BTN_GAP         = 10


class ItemRenderer:
    """Handles all rendering for the item scene."""

    def __init__(self, effect_handler: ItemEffectHandler,
                 mc_catalog: MagicCoreCatalogState | None = None) -> None:
        self._effect_handler = effect_handler
        self._mc_catalog = mc_catalog
        self._fonts_ready = False
        self._view = ItemSelectionView(
            ItemSelectionTheme(),
            row_h=ITEM_ROW_H,
            row_gap=ITEM_ROW_GAP,
            font_size=14,
            sub_font_size=11,
        )
        # Show a half-row peek of the 16th item.
        self._view.PEEK_RATIO = PEEK_RATIO

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title  = f.get(20, bold=True)
        self._font_tab    = f.get(14, bold=True)
        self._font_item   = f.get(14)
        self._font_qty    = f.get(13)
        self._font_detail = f.get(14)
        self._font_btn    = f.get(14, bold=True)
        self._font_hint   = f.get(13)
        self._font_gp     = f.get(16)
        self._fonts_ready = True

    @property
    def fonts_ready(self) -> bool:
        return self._fonts_ready

    def render(self, screen: pygame.Surface, gp: int, tab_index: int,
               items: list[ItemEntry], list_sel: int, scroll: int,
               in_tab: bool, in_action: bool, action_sel: int,
               selected_entry: ItemEntry | None,
               confirm_discard: bool, discard_qty: int, aoe_confirm: bool,
               target_overlay,
               in_filter: bool,
               filter_items: list[ItemEntry],
               filter_sel: int,
               filter_scroll: int,
               hidden_ids: set[str],
               edit_tags: bool = False,
               editor_rows: list | None = None,
               editor_sel: int = 0,
               tag_warning: str = "",
               in_new_tag: bool = False,
               tag_input: str = "") -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)
        self._draw_header(screen, gp)
        self._draw_tabs(screen, tab_index, in_tab)

        panel_top    = PAD + HEADER_H + TAB_H + TAB_GAP * 2
        panel_bottom = screen.get_height() - FOOTER_H - PAD
        panel_h      = panel_bottom - panel_top

        filter_x = PAD
        list_x   = PAD + FILTER_W + PAD
        det_x    = list_x + LIST_W + PAD
        det_w    = screen.get_width() - det_x - PAD

        self._draw_filter_panel(screen, filter_x, panel_top, FILTER_W, panel_h,
                                filter_items, filter_sel, filter_scroll,
                                in_filter, hidden_ids)
        list_active = not in_tab and not in_filter
        self._draw_list_panel(screen, list_x, panel_top, LIST_W, panel_h,
                              items, list_sel, scroll, list_active)
        # Detail only shows when the cursor is actually on a list item.
        show_detail = not in_tab and not in_filter
        self._draw_detail_panel(screen, det_x, panel_top, det_w, panel_h,
                                selected_entry if show_detail else None,
                                in_action, action_sel)
        self._draw_footer(screen)

        if confirm_discard:
            self._draw_confirm_overlay(screen, selected_entry, discard_qty)
        if aoe_confirm:
            self._draw_aoe_confirm_overlay(screen, selected_entry)
        if target_overlay:
            target_overlay.render(screen)
        if edit_tags:
            self._draw_edit_tags_overlay(
                screen, selected_entry, editor_rows or [], editor_sel,
                tag_warning,
            )
            if in_new_tag:
                self._draw_new_tag_overlay(screen, tag_input)

    # ── Header ────────────────────────────────────────────────

    def _draw_header(self, screen: pygame.Surface, gp: int) -> None:
        render_header(screen, self._font_title, self._font_hint,
                      "ITEMS", "use, sort, and inspect supplies", PAD, PAD - 8)
        gp_val   = self._font_gp.render(f"{gp}", True, TEXT_PRIMARY)
        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gx = screen.get_width() - PAD - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD + 6))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD + 6))
        draw_divider(screen, PAD, PAD + HEADER_H - 2, screen.get_width() - PAD * 2)

    # ── Tabs ──────────────────────────────────────────────────

    def _draw_tabs(self, screen: pygame.Surface, tab_index: int, in_tab: bool) -> None:
        tab_y = PAD + HEADER_H + TAB_GAP
        avail = screen.get_width() - 2 * PAD
        n     = len(TABS)
        tw    = (avail - TAB_GAP * (n - 1)) // n
        for i, label in enumerate(TABS):
            x      = PAD + i * (tw + TAB_GAP)
            active = (i == tab_index)
            render_row_frame(screen, pygame.Rect(x, tab_y, tw, TAB_H),
                             focused=active and in_tab, dimmed_sel=active)
            col = HEADER_COLOR if active else TEXT_SECONDARY
            txt = self._font_tab.render(label, True, col)
            screen.blit(txt, (x + (tw - txt.get_width()) // 2,
                              tab_y + (TAB_H - txt.get_height()) // 2))

    # ── Filter panel ──────────────────────────────────────────

    def _draw_filter_panel(self, screen: pygame.Surface,
                           x: int, y: int, w: int, h: int,
                           items: list[ItemEntry], sel: int, scroll: int,
                           in_filter: bool, hidden_ids: set[str]) -> None:
        render_panel(screen, pygame.Rect(x, y, w, h), active=in_filter)

        if not items:
            empty = self._font_hint.render("No items.", True, TEXT_DIM)
            screen.blit(empty, (x + 12, y + 12))
            return

        rows = [
            ItemRow(
                title=display_name(entry, self._mc_catalog),
                right_text="off" if entry.id in hidden_ids else "on",
                locked=entry.id in hidden_ids,
            )
            for entry in items
        ]
        has_overflow = len(items) > VISIBLE_ROWS
        list_rect_h = self._view.list_height(VISIBLE_ROWS, has_overflow)
        list_rect = pygame.Rect(x + 6, y + 6, w - 12, list_rect_h)
        self._view.render(
            screen, list_rect, rows, sel, scroll,
            active=in_filter,
        )

    # ── List panel ────────────────────────────────────────────

    def _draw_list_panel(self, screen: pygame.Surface,
                         x: int, y: int, w: int, h: int,
                         items: list[ItemEntry], list_sel: int, scroll: int,
                         active: bool) -> None:
        render_panel(screen, pygame.Rect(x, y, w, h), active=active)

        if not items:
            empty = self._font_detail.render("No items.", True, TEXT_DIM)
            screen.blit(empty, (x + 16, y + 16))
            return

        rows = [
            ItemRow(
                title=display_name(entry, self._mc_catalog),
                right_text=f"x {entry.qty}",
                locked=entry.locked,
            )
            for entry in items
        ]
        has_overflow = len(items) > VISIBLE_ROWS
        list_rect_h = self._view.list_height(VISIBLE_ROWS, has_overflow)
        list_rect = pygame.Rect(x + 6, y + 6, w - 12, list_rect_h)
        self._view.render(
            screen, list_rect, rows, list_sel, scroll,
            active=active,
        )

    # ── Detail panel ──────────────────────────────────────────

    def _draw_detail_panel(self, screen: pygame.Surface,
                           x: int, y: int, w: int, h: int,
                           entry: ItemEntry | None,
                           in_action: bool, action_sel: int) -> None:
        render_panel(screen, pygame.Rect(x, y, w, h))

        if not entry:
            return

        cx, cy = x + 16, y + 16

        name = display_name(entry, self._mc_catalog)
        screen.blit(self._font_title.render(name, True, HEADER_COLOR), (cx, cy))
        cy += self._font_title.get_height() + 4

        qty_surf = self._font_detail.render(f"Quantity:  {entry.qty}", True, TEXT_SECONDARY)
        screen.blit(qty_surf, (cx, cy))
        cy += qty_surf.get_height() + 14

        pygame.draw.line(screen, DIVIDER, (cx, cy), (x + w - 16, cy))
        cy += 12

        desc = entry.description or "No description available."
        cy   = self._draw_wrapped(screen, desc, cx, cy, w - 32, TEXT_PRIMARY)
        cy  += 20

        if entry.tags:
            tag_str  = "  ".join(f"[{t}]" for t in sorted(entry.tags))
            tag_surf = self._font_hint.render(tag_str, True, MUTED)
            screen.blit(tag_surf, (cx, cy))
            cy += tag_surf.get_height() + 20

        pygame.draw.line(screen, DIVIDER, (cx, cy), (x + w - 16, cy))
        cy += 16

        item_actions = actions_for(entry, self._effect_handler)
        for i, label in enumerate(item_actions):
            is_sel   = in_action and (i == action_sel)
            disabled = (label == "Discard" and entry.locked)
            col = BTN_TEXT_DIS if disabled else (INK if is_sel else BTN_TEXT)

            render_row_frame(screen, pygame.Rect(cx, cy, BTN_W, BTN_H),
                             focused=is_sel, dimmed_sel=not is_sel)
            lbl_surf = self._font_btn.render(label, True, col)
            screen.blit(lbl_surf, (cx + BTN_W // 2 - lbl_surf.get_width() // 2,
                                   cy + BTN_H // 2 - lbl_surf.get_height() // 2))
            cy += BTN_H + BTN_GAP

    def _draw_wrapped(self, screen: pygame.Surface, text: str,
                      x: int, y: int, max_w: int, color: tuple) -> int:
        words  = text.split()
        line, line_y = "", y
        lh     = self._font_detail.get_height() + 3
        for word in words:
            test = (line + " " + word).strip()
            if self._font_detail.size(test)[0] > max_w and line:
                screen.blit(self._font_detail.render(line, True, color), (x, line_y))
                line, line_y = word, line_y + lh
            else:
                line = test
        if line:
            screen.blit(self._font_detail.render(line, True, color), (x, line_y))
            line_y += lh
        return line_y

    # ── Confirm overlays ──────────────────────────────────────

    def _draw_confirm_overlay(self, screen: pygame.Surface,
                              entry: ItemEntry | None, qty: int) -> None:
        name  = entry.id.replace("_", " ").title() if entry else "item"
        total = entry.qty if entry else 1
        ow, oh = 440, 150
        modal = render_modal(screen, ow, oh)
        ox, oy = modal.x, modal.y

        msg = self._font_detail.render(f"Discard {name}?", True, EMBER)
        screen.blit(msg, (ox + 20, oy + 16))

        # Quantity stepper:  <  qty / total  >
        at_min = qty <= 1
        at_max = qty >= total
        left_col  = DIM if at_min else INK
        right_col = DIM if at_max else INK
        cy = oy + 54
        screen.blit(self._font_title.render("<", True, left_col), (ox + 24, cy))
        amount = self._font_title.render(f"{qty} / {total}", True, INK)
        screen.blit(amount, (ox + ow // 2 - amount.get_width() // 2, cy))
        rx = ox + ow - 24 - self._font_title.size(">")[0]
        screen.blit(self._font_title.render(">", True, right_col), (rx, cy))

        render_hint(screen, self._font_hint,
                    "←/→ qty    ENTER / Y - Confirm    ESC / N - Cancel",
                    ox + 20, oy + oh - 30)

    def _draw_aoe_confirm_overlay(self, screen: pygame.Surface, entry: ItemEntry | None) -> None:
        name  = entry.id.replace("_", " ").title() if entry else "item"
        ow, oh = 460, 110
        modal = render_modal(screen, ow, oh)
        ox, oy = modal.x, modal.y
        msg  = self._font_detail.render(
            f"Use {name} on the whole party?", True, C_CONFIRM_TXT)
        screen.blit(msg,  (ox + 20, oy + 18))
        render_hint(screen, self._font_hint,
                    "ENTER / Y - Confirm    ESC / N - Cancel", ox + 20, oy + 58)

    # ── Footer ────────────────────────────────────────────────

    # \u2500\u2500 Edit Tags overlay \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _draw_edit_tags_overlay(self, screen: pygame.Surface,
                                entry: ItemEntry | None,
                                rows: list, sel: int,
                                warning: str) -> None:
        if not entry:
            return
        ow, oh = 420, 360
        modal = render_modal(screen, ow, oh)
        ox, oy = modal.x, modal.y

        cx, cy = ox + 16, oy + 14
        title_text = f"Edit Tags: {entry.name or entry.id}"
        screen.blit(
            self._font_title.render(title_text, True, HEADER_COLOR), (cx, cy),
        )
        cy += self._font_title.get_height() + 8
        draw_divider(screen, cx, cy, ow - 32)
        cy += 10

        last_section: str | None = None
        for i, row in enumerate(rows):
            kind, tag = row
            section = (
                "System Tags" if kind == "system" else
                "Custom Tags" if kind in ("custom", "new") else None
            )
            if section and section != last_section:
                if last_section is not None:
                    cy += 6
                lbl = self._font_hint.render(section, True, TEXT_SECONDARY)
                screen.blit(lbl, (cx, cy))
                cy += lbl.get_height() + 4
                last_section = section

            row_h = 24
            if i == sel:
                render_row_frame(screen,
                                 pygame.Rect(cx - 4, cy - 2, ow - 28, row_h),
                                 focused=True)

            if kind == "new":
                label = "[+] New Tag..."
                col   = BTN_TEXT
            else:
                checked = tag in entry.tags
                box     = "[x]" if checked else "[ ]"
                label   = f"{box} {tag}"
                col     = TEXT_PRIMARY if checked else TEXT_SECONDARY
            screen.blit(self._font_detail.render(label, True, col), (cx + 4, cy))
            cy += row_h

        cy = oy + oh - 56
        draw_divider(screen, cx, cy, ow - 32)
        cy += 6
        count_str = f"Tags: {len(entry.tags)}/5"
        screen.blit(self._font_hint.render(count_str, True, TEXT_SECONDARY), (cx, cy))
        if warning:
            warn = self._font_hint.render(warning, True, EMBER)
            screen.blit(warn, (ox + ow - 16 - warn.get_width(), cy))
        cy += 18
        screen.blit(
            self._font_hint.render(
                "ENTER toggle \u00b7 ESC close", True, MUTED,
            ),
            (cx, cy),
        )

    def _draw_new_tag_overlay(self, screen: pygame.Surface, text: str) -> None:
        ow, oh = 360, 110
        modal = render_modal(screen, ow, oh)
        ox, oy = modal.x, modal.y
        cx, cy = ox + 16, oy + 14
        screen.blit(self._font_title.render("New Tag", True, HEADER_COLOR), (cx, cy))
        cy += self._font_title.get_height() + 6
        box_w, box_h = ow - 32, 28
        pygame.draw.rect(screen, (12, 12, 16), (cx, cy, box_w, box_h), border_radius=4)
        pygame.draw.rect(screen, BORDER_ACTIVE, (cx, cy, box_w, box_h), 1, border_radius=4)
        screen.blit(
            self._font_detail.render(text + "|", True, TEXT_PRIMARY),
            (cx + 6, cy + (box_h - self._font_detail.get_height()) // 2),
        )
        cy += box_h + 6
        render_hint(screen, self._font_hint, "ENTER confirm \u00b7 ESC cancel", cx, cy)

    # \u2500\u2500 Footer \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = screen.get_height() - FOOTER_H
        draw_divider(screen, PAD, fy, screen.get_width() - PAD * 2)
        render_hint(screen, self._font_hint,
                    "navigate \u00b7 \u2190 filter \u00b7 ENTER toggle/act \u00b7 T edit tags \u00b7 I close",
                    PAD, fy + 8)
