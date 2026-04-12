# engine/ui/item_renderer.py
#
# Item scene rendering — all drawing, fonts, layout.
# Extracted from item_scene.py to separate rendering from data logic.

from __future__ import annotations

import pygame
from engine.common.item_entry_state import ItemEntry
from engine.item.item_logic import TABS, actions_for, display_name
from engine.item.magic_core_catalog_state import MagicCoreCatalogState
from engine.item.item_effect_handler import ItemEffectHandler

# ── Colors ────────────────────────────────────────────────────
BG_COLOR        = (26, 26, 46)
HEADER_COLOR    = (212, 200, 138)
MUTED           = (100, 100, 110)
TEXT_PRIMARY    = (238, 238, 238)
TEXT_SECONDARY  = (170, 170, 170)
TEXT_DIM        = (80, 80, 90)
TEXT_NEW        = (140, 220, 140)

TAB_BG_ACT      = (55, 55, 90)
TAB_BG_NORM     = (35, 35, 55)
TAB_BORDER_ACT  = (212, 200, 138)
TAB_BORDER_NORM = (60, 60, 85)

LIST_BG         = (30, 30, 50)
LIST_SEL_BG     = (50, 50, 85)
LIST_SEL_BDR    = (212, 200, 138)
LIST_NORM_BDR   = (45, 45, 68)
LIST_PRE_BG     = (38, 38, 62)
LIST_PRE_BDR    = (100, 95, 130)

DETAIL_BG       = (32, 32, 54)
DETAIL_BDR      = (55, 55, 80)

BTN_BG          = (55, 45, 80)
BTN_BG_HOV      = (75, 60, 110)
BTN_BG_DIS      = (38, 38, 55)
BTN_BDR         = (130, 100, 180)
BTN_BDR_DIS     = (55, 55, 70)
BTN_TEXT        = (220, 200, 255)
BTN_TEXT_DIS    = (80, 80, 95)

C_CONFIRM_BG    = (28, 22, 10)
C_CONFIRM_BDR   = (180, 150, 60)
C_CONFIRM_TXT   = (230, 200, 120)

DIVIDER         = (55, 55, 78)

# ── Layout ────────────────────────────────────────────────────
PAD             = 16
HEADER_H        = 44
TAB_H           = 34
TAB_GAP         = 4
FOOTER_H        = 30

LIST_W          = 480
ITEM_ROW_H      = 36
ITEM_ROW_GAP    = 2
VISIBLE_ROWS    = 14

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

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 20, bold=True)
        self._font_tab    = pygame.font.SysFont("Arial", 14, bold=True)
        self._font_item   = pygame.font.SysFont("Arial", 14)
        self._font_qty    = pygame.font.SysFont("Arial", 13)
        self._font_detail = pygame.font.SysFont("Arial", 14)
        self._font_btn    = pygame.font.SysFont("Arial", 14, bold=True)
        self._font_hint   = pygame.font.SysFont("Arial", 13)
        self._font_gp     = pygame.font.SysFont("Arial", 16)
        self._font_new    = pygame.font.SysFont("Arial", 11, bold=True)
        self._fonts_ready = True

    @property
    def fonts_ready(self) -> bool:
        return self._fonts_ready

    def render(self, screen: pygame.Surface, gp: int, tab_index: int,
               items: list[ItemEntry], list_sel: int, scroll: int,
               in_tab: bool, in_action: bool, action_sel: int,
               selected_entry: ItemEntry | None,
               confirm_discard: bool, aoe_confirm: bool,
               target_overlay) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(BG_COLOR)
        self._draw_header(screen, gp)
        self._draw_tabs(screen, tab_index, in_tab)

        panel_top    = PAD + HEADER_H + TAB_H + TAB_GAP * 2
        panel_bottom = screen.get_height() - FOOTER_H - PAD
        panel_h      = panel_bottom - panel_top

        list_x = PAD
        det_x  = PAD + LIST_W + PAD
        det_w  = screen.get_width() - det_x - PAD

        self._draw_list_panel(screen, list_x, panel_top, LIST_W, panel_h,
                              items, list_sel, scroll, tab_index, in_tab, in_action)
        self._draw_detail_panel(screen, det_x, panel_top, det_w, panel_h,
                                selected_entry, in_action, action_sel)
        self._draw_footer(screen)

        if confirm_discard:
            self._draw_confirm_overlay(screen, selected_entry)
        if aoe_confirm:
            self._draw_aoe_confirm_overlay(screen, selected_entry)
        if target_overlay:
            target_overlay.render(screen)

    # ── Header ────────────────────────────────────────────────

    def _draw_header(self, screen: pygame.Surface, gp: int) -> None:
        title = self._font_title.render("ITEMS", True, HEADER_COLOR)
        screen.blit(title, (PAD, PAD + 6))
        gp_val   = self._font_gp.render(f"{gp}", True, TEXT_PRIMARY)
        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gx = screen.get_width() - PAD - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD + 6))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD + 6))
        pygame.draw.line(screen, DIVIDER,
                         (PAD, PAD + HEADER_H - 2),
                         (screen.get_width() - PAD, PAD + HEADER_H - 2))

    # ── Tabs ──────────────────────────────────────────────────

    def _draw_tabs(self, screen: pygame.Surface, tab_index: int, in_tab: bool) -> None:
        tab_y = PAD + HEADER_H + TAB_GAP
        x = PAD
        for i, label in enumerate(TABS):
            active = (i == tab_index)
            surf   = self._font_tab.render(label, True, TEXT_PRIMARY)
            tw     = surf.get_width() + 24
            bg     = TAB_BG_ACT  if active else TAB_BG_NORM
            bdr    = (TAB_BORDER_ACT if in_tab else TAB_BORDER_NORM) if active else TAB_BORDER_NORM
            pygame.draw.rect(screen, bg,  (x, tab_y, tw, TAB_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (x, tab_y, tw, TAB_H), 1, border_radius=4)
            col = HEADER_COLOR if active else TEXT_SECONDARY
            txt = self._font_tab.render(label, True, col)
            screen.blit(txt, (x + 12, tab_y + (TAB_H - txt.get_height()) // 2))
            x += tw + TAB_GAP

    # ── List panel ────────────────────────────────────────────

    def _draw_list_panel(self, screen: pygame.Surface,
                         x: int, y: int, w: int, h: int,
                         items: list[ItemEntry], list_sel: int, scroll: int,
                         tab_index: int, in_tab: bool, in_action: bool) -> None:
        pygame.draw.rect(screen, LIST_BG, (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, DIVIDER, (x, y, w, h), 1, border_radius=6)

        tab = TABS[tab_index]

        if not items:
            empty = self._font_detail.render("No items.", True, TEXT_DIM)
            screen.blit(empty, (x + 16, y + 16))
            return

        row_y = y + 6
        for i in range(VISIBLE_ROWS):
            idx = scroll + i
            if idx >= len(items):
                break
            entry  = items[idx]
            sel    = (idx == list_sel)
            rx, rw = x + 6, w - 12

            if sel and in_tab:
                bg  = LIST_PRE_BG
                bdr = LIST_PRE_BDR
            elif sel:
                bg  = LIST_SEL_BG
                bdr = LIST_SEL_BDR
            else:
                bg  = LIST_BG
                bdr = LIST_NORM_BDR
            pygame.draw.rect(screen, bg,  (rx, row_y, rw, ITEM_ROW_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (rx, row_y, rw, ITEM_ROW_H), 1, border_radius=4)

            if sel and not in_action and not in_tab:
                cur = self._font_item.render("\u25b6", True, HEADER_COLOR)
                screen.blit(cur, (rx + 4, row_y + (ITEM_ROW_H - cur.get_height()) // 2))

            badge_x = rx + 20
            if tab == "New" and idx < 3:
                badge = self._font_new.render("NEW", True, TEXT_NEW)
                screen.blit(badge, (badge_x, row_y + (ITEM_ROW_H - badge.get_height()) // 2))
                badge_x += badge.get_width() + 6

            name = display_name(entry, self._mc_catalog)
            locked_marker = " \U0001f512" if entry.locked else ""
            name_col  = TEXT_DIM if entry.locked else (TEXT_PRIMARY if (sel and not in_tab) else TEXT_SECONDARY)
            name_surf = self._font_item.render(name + locked_marker, True, name_col)
            screen.blit(name_surf, (badge_x, row_y + (ITEM_ROW_H - name_surf.get_height()) // 2))

            qty_surf = self._font_qty.render(
                f"\u00d7 {entry.qty}", True, HEADER_COLOR if (sel and not in_tab) else MUTED)
            screen.blit(qty_surf, (rx + rw - qty_surf.get_width() - 10,
                                   row_y + (ITEM_ROW_H - qty_surf.get_height()) // 2))

            row_y += ITEM_ROW_H + ITEM_ROW_GAP

        if scroll > 0:
            up = self._font_hint.render("\u25b2", True, MUTED)
            screen.blit(up, (x + w - up.get_width() - 8, y + 4))
        if scroll + VISIBLE_ROWS < len(items):
            dn = self._font_hint.render("\u25bc", True, MUTED)
            screen.blit(dn, (x + w - dn.get_width() - 8, y + h - dn.get_height() - 4))

    # ── Detail panel ──────────────────────────────────────────

    def _draw_detail_panel(self, screen: pygame.Surface,
                           x: int, y: int, w: int, h: int,
                           entry: ItemEntry | None,
                           in_action: bool, action_sel: int) -> None:
        pygame.draw.rect(screen, DETAIL_BG, (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, DETAIL_BDR, (x, y, w, h), 1, border_radius=6)

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
            bg  = BTN_BG_DIS  if disabled else (BTN_BG_HOV if is_sel else BTN_BG)
            bdr = BTN_BDR_DIS if disabled else (TAB_BORDER_ACT if is_sel else BTN_BDR)
            col = BTN_TEXT_DIS if disabled else BTN_TEXT

            pygame.draw.rect(screen, bg,  (cx, cy, BTN_W, BTN_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (cx, cy, BTN_W, BTN_H), 1, border_radius=4)
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

    def _draw_confirm_overlay(self, screen: pygame.Surface, entry: ItemEntry | None) -> None:
        name  = entry.id.replace("_", " ").title() if entry else "item"
        ow, oh = 420, 110
        ox = (screen.get_width()  - ow) // 2
        oy = (screen.get_height() - oh) // 2
        pygame.draw.rect(screen, (30, 15, 20), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, (180, 70, 70), (ox, oy, ow, oh), 2, border_radius=6)
        msg  = self._font_detail.render(f"Discard {name}?", True, (220, 180, 180))
        hint = self._font_hint.render("ENTER / Y \u2014 Confirm    ESC / N \u2014 Cancel", True, (160, 120, 120))
        screen.blit(msg,  (ox + 20, oy + 18))
        screen.blit(hint, (ox + 20, oy + 58))

    def _draw_aoe_confirm_overlay(self, screen: pygame.Surface, entry: ItemEntry | None) -> None:
        name  = entry.id.replace("_", " ").title() if entry else "item"
        ow, oh = 460, 110
        ox = (screen.get_width()  - ow) // 2
        oy = (screen.get_height() - oh) // 2
        pygame.draw.rect(screen, C_CONFIRM_BG,  (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_CONFIRM_BDR, (ox, oy, ow, oh), 2, border_radius=6)
        msg  = self._font_detail.render(
            f"Use {name} on the whole party?", True, C_CONFIRM_TXT)
        hint = self._font_hint.render(
            "ENTER / Y \u2014 Confirm    ESC / N \u2014 Cancel", True, MUTED)
        screen.blit(msg,  (ox + 20, oy + 18))
        screen.blit(hint, (ox + 20, oy + 58))

    # ── Footer ────────────────────────────────────────────────

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = screen.get_height() - FOOTER_H
        pygame.draw.line(screen, DIVIDER, (PAD, fy), (screen.get_width() - PAD, fy))
        hint = self._font_hint.render(
            "\u2191\u2193 navigate \u00b7 Q/E tab \u00b7 \u2192 actions \u00b7 I close", True, MUTED)
        screen.blit(hint, (PAD, fy + 8))
