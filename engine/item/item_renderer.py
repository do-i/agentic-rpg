# engine/item/item_renderer.py
#
# Item scene rendering — three-column wizard (Pouch | List | Detail) plus the
# action / discard / aoe / tags / new-tag / manage modal overlays. All drawing,
# fonts and layout live here; the scene owns state and navigation.

from __future__ import annotations

import pygame

from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.ui.theme import BORDER_ACTIVE, DIM, EMBER, GOLD, INK, MUTED
from engine.common.ui.chrome import (
    draw_divider,
    icon_surface,
    render_backdrop,
    render_header,
    render_hint,
    render_icon_row,
    render_modal,
    render_panel,
    render_row_frame,
    wrap_text,
)
from engine.item.item_entry_state import ItemEntry
from engine.item.item_logic import TABS, display_name
from engine.item.magic_core_catalog_state import MagicCoreCatalogState
from engine.item.item_effect_handler import ItemEffectHandler

PAGE_POUCH = "pouch"
PAGE_LIST  = "list"

PAD_X, PAD_Y, GAP = 40, 30, 18
POUCH_W = 300
LIST_W  = 430
ROW_H   = 50
ROW_GAP = 6

C_CONFIRM = GOLD


class ItemRenderer:
    """All rendering for the three-column item wizard and its modals."""

    def __init__(self, effect_handler: ItemEffectHandler,
                 mc_catalog: MagicCoreCatalogState | None = None) -> None:
        self._effect_handler = effect_handler
        self._mc_catalog = mc_catalog
        self._fonts_ready = False

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_head  = f.get(18, bold=True)
        self._font_row   = f.get(18)
        self._font_stat  = f.get(16)
        self._font_meta  = f.get(CAPTION)
        self._font_hint  = f.get(14)
        self._fonts_ready = True

    # ── Entry point ───────────────────────────────────────────

    def render(self, screen: pygame.Surface, *,
               gp: int, page_id: str, tab_index: int, tab_counts: list[int],
               items: list[ItemEntry], list_sel: int,
               selected_entry: ItemEntry | None,
               modal: str | None,
               action_options: list[str], action_sel: int,
               discard_qty: int,
               manage_entries: list[ItemEntry], manage_sel: int,
               hidden_ids: set[str],
               editor_rows: list, editor_sel: int,
               tag_warning: str, tag_input: str,
               target_overlay) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)
        subtitle = TABS[tab_index] if page_id == PAGE_LIST else "pick a pouch"
        render_header(screen, self._font_title, self._font_hint,
                      "ITEMS", subtitle, PAD_X, PAD_Y)
        gp_surf = self._font_stat.render(f"GP  {gp}", True, GOLD)
        screen.blit(gp_surf, (screen.get_width() - PAD_X - gp_surf.get_width(),
                              PAD_Y + 6))

        pouch_rect, list_rect, det_rect = self._layout(screen)
        self._draw_pouch(screen, pouch_rect, tab_index, tab_counts,
                         active=page_id == PAGE_POUCH)
        # Items + Detail columns stay hidden until a pouch is opened.
        if page_id == PAGE_LIST:
            self._draw_list(screen, list_rect, items, list_sel, page_id)
            self._draw_detail(screen, det_rect, selected_entry, page_id)
        self._draw_footer(screen, page_id)

        # Modal overlays (mutually exclusive, drawn over the columns).
        if modal == "action":
            self._draw_action_modal(screen, selected_entry,
                                     action_options, action_sel)
        elif modal == "discard":
            self._draw_discard_modal(screen, selected_entry, discard_qty)
        elif modal == "aoe":
            self._draw_aoe_modal(screen, selected_entry)
        elif modal == "manage":
            self._draw_manage_modal(screen, manage_entries, manage_sel, hidden_ids)
        if modal in ("tags", "newtag"):
            self._draw_tags_modal(screen, selected_entry, editor_rows,
                                  editor_sel, tag_warning)
            if modal == "newtag":
                self._draw_new_tag_modal(screen, tag_input)
        if target_overlay:
            target_overlay.render(screen)

    # ── Layout ────────────────────────────────────────────────

    def _layout(self, screen: pygame.Surface):
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        ph = sh - top - 56
        det_w = sw - PAD_X * 2 - GAP * 2 - POUCH_W - LIST_W
        pouch = pygame.Rect(PAD_X, top, POUCH_W, ph)
        lst = pygame.Rect(pouch.right + GAP, top, LIST_W, ph)
        det = pygame.Rect(lst.right + GAP, top, det_w, ph)
        return pouch, lst, det

    # ── Pouch column ──────────────────────────────────────────

    def _draw_pouch(self, screen, panel, tab_index, counts, *, active) -> None:
        render_panel(screen, panel, active=active, title="Pouch",
                     title_font=self._font_head)
        x, y = panel.x + 14, panel.y + 50
        n = len(TABS)
        avail = panel.bottom - 14 - y
        rh = min(56, (avail - ROW_GAP * (n - 1)) // n)
        for i, label in enumerate(TABS):
            r = pygame.Rect(x, y + i * (rh + ROW_GAP), panel.w - 28, rh)
            count = counts[i] if i < len(counts) else 0
            render_icon_row(
                screen, self._font_row, r, label,
                icon_key=f"pouch_{label}",
                focused=active and i == tab_index,
                dimmed_sel=(not active) and i == tab_index,
                color=INK if count else DIM,
                right_text=str(count), right_font=self._font_meta,
            )

    # ── List column ───────────────────────────────────────────

    def _draw_list(self, screen, panel, items, list_sel, page_id) -> None:
        render_panel(screen, panel, active=True, title="Items",
                     title_font=self._font_head)

        if not items:
            msg = self._font_row.render("Pouch is empty.", True, DIM)
            screen.blit(msg, (panel.x + 16, panel.y + 56))
            hint = self._font_meta.render("press M to manage hidden items",
                                          True, MUTED)
            screen.blit(hint, (panel.x + 16, panel.y + 56 + msg.get_height() + 6))
            return

        x, y = panel.x + 14, panel.y + 50
        list_w = panel.w - 28
        step = ROW_H + ROW_GAP
        max_rows = max(1, (panel.bottom - 14 - y) // step)
        first = max(0, min(list_sel - max_rows + 1,
                           max(0, len(items) - max_rows)))
        for i in range(first, min(first + max_rows, len(items))):
            entry = items[i]
            r = pygame.Rect(x, y + (i - first) * step, list_w, ROW_H)
            render_icon_row(
                screen, self._font_row, r, display_name(entry, self._mc_catalog),
                icon_key=f"item_{entry.id}",
                focused=i == list_sel,
                dimmed_sel=False,
                color=INK,
                right_text=f"x{entry.qty}", right_font=self._font_meta,
                subtext=_short_desc(entry), sub_font=self._font_meta,
            )

    # ── Detail column ─────────────────────────────────────────

    def _draw_detail(self, screen, panel, entry, page_id) -> None:
        render_panel(screen, panel, active=False, title="Detail",
                     title_font=self._font_head)
        if entry is None:
            return

        cx, cy = panel.x + 18, panel.y + 50
        icon = icon_surface(f"item_{entry.id}", 56)
        screen.blit(icon, (cx, cy))
        name = display_name(entry, self._mc_catalog)
        screen.blit(self._font_title.render(name, True, GOLD), (cx + 70, cy + 2))
        screen.blit(self._font_meta.render(f"Quantity  x{entry.qty}", True, MUTED),
                    (cx + 70, cy + 32))
        cy += 78
        draw_divider(screen, cx, cy, panel.w - 36)
        cy += 14

        desc = entry.description or "No description available."
        for line in wrap_text(self._font_meta, desc, panel.w - 36):
            screen.blit(self._font_meta.render(line, True, INK), (cx, cy))
            cy += self._font_meta.get_height() + 3
        cy += 10

        if entry.tags:
            cy = self._draw_chips(screen, cx, cy, panel.w - 36, sorted(entry.tags))
            cy += 8

        draw_divider(screen, cx, cy, panel.w - 36)
        cy += 12
        screen.blit(self._font_hint.render("ENTER  ->  actions", True, MUTED),
                    (cx, cy))

    def _draw_chips(self, screen, x, y, max_w, tags) -> int:
        tx, ty = x, y
        for tag in tags:
            s = self._font_hint.render(tag, True, (20, 17, 12))
            cw = s.get_width() + 16
            if tx + cw > x + max_w:
                tx = x
                ty += 28
            chip = pygame.Rect(tx, ty, cw, 22)
            pygame.draw.rect(screen, GOLD, chip, border_radius=11)
            screen.blit(s, (chip.x + 8, chip.y + 3))
            tx += cw + 8
        return ty + 28

    # ── Footer ────────────────────────────────────────────────

    def _draw_footer(self, screen, page_id) -> None:
        sw, sh = screen.get_size()
        text = {
            PAGE_POUCH: "UP/DOWN choose pouch   ENTER open   I close",
            PAGE_LIST:  "UP/DOWN browse   ENTER actions   M manage   ESC back   I close",
        }[page_id]
        draw_divider(screen, PAD_X, sh - 38, sw - PAD_X * 2)
        hint = self._font_hint.render(text, True, DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))

    # ── Action modal ──────────────────────────────────────────

    def _draw_action_modal(self, screen, entry, options, sel) -> None:
        if not entry:
            return
        title = display_name(entry, self._mc_catalog)
        mw, mh = 280, 64 + len(options) * 50
        modal = render_modal(screen, mw, mh, title=title,
                             title_font=self._font_head)
        subs = {
            "Use": "use this item",
            "Discard": "drop from pouch",
            "Edit Tags": "curate tags",
        }
        for i, label in enumerate(options):
            r = pygame.Rect(modal.x + 12, modal.y + 50 + i * 48, mw - 24, 42)
            render_row_frame(screen, r, focused=(i == sel))
            screen.blit(self._font_row.render(label, True, INK),
                        (r.x + 12, r.y + 3))
            screen.blit(self._font_hint.render(subs.get(label, ""), True, MUTED),
                        (r.x + 12, r.y + 24))

    # ── Discard modal ─────────────────────────────────────────

    def _draw_discard_modal(self, screen, entry, qty) -> None:
        name = display_name(entry, self._mc_catalog) if entry else "item"
        total = entry.qty if entry else 1
        mw, mh = 440, 150
        modal = render_modal(screen, mw, mh)
        ox, oy = modal.x, modal.y
        screen.blit(self._font_row.render(f"Discard {name}?", True, EMBER),
                    (ox + 20, oy + 16))
        at_min, at_max = qty <= 1, qty >= total
        cy = oy + 56
        screen.blit(self._font_title.render("<", True, DIM if at_min else INK),
                    (ox + 24, cy))
        amount = self._font_title.render(f"{qty} / {total}", True, INK)
        screen.blit(amount, (ox + mw // 2 - amount.get_width() // 2, cy))
        rx = ox + mw - 24 - self._font_title.size(">")[0]
        screen.blit(self._font_title.render(">", True, DIM if at_max else INK),
                    (rx, cy))
        render_hint(screen, self._font_hint,
                    "LEFT/RIGHT qty   ENTER / Y confirm   ESC / N cancel",
                    ox + 20, oy + mh - 30)

    # ── AOE confirm modal ─────────────────────────────────────

    def _draw_aoe_modal(self, screen, entry) -> None:
        name = display_name(entry, self._mc_catalog) if entry else "item"
        mw, mh = 460, 110
        modal = render_modal(screen, mw, mh)
        ox, oy = modal.x, modal.y
        screen.blit(self._font_row.render(
            f"Use {name} on the whole party?", True, C_CONFIRM), (ox + 20, oy + 18))
        render_hint(screen, self._font_hint,
                    "ENTER / Y confirm   ESC / N cancel", ox + 20, oy + 58)

    # ── Manage (show/hide) modal ──────────────────────────────

    def _draw_manage_modal(self, screen, entries, sel, hidden_ids) -> None:
        mw, mh = 540, 470
        modal = render_modal(screen, mw, mh, title="Manage Pouch",
                             title_font=self._font_head)
        cx, cy = modal.x + 20, modal.y + 50
        screen.blit(self._font_meta.render(
            "Toggle which items show in the list.", True, MUTED), (cx, cy))
        cy += 30
        if not entries:
            screen.blit(self._font_row.render("No items.", True, DIM), (cx, cy))
            return
        row_h, gap = 40, 6
        list_top = cy
        max_rows = max(1, (modal.bottom - 44 - list_top) // (row_h + gap))
        first = max(0, min(sel - max_rows + 1, max(0, len(entries) - max_rows)))
        for i in range(first, min(first + max_rows, len(entries))):
            entry = entries[i]
            r = pygame.Rect(cx, list_top + (i - first) * (row_h + gap),
                            mw - 40, row_h)
            render_row_frame(screen, r, focused=(i == sel))
            shown = entry.id not in hidden_ids
            box = "[x]" if shown else "[ ]"
            col = INK if shown else DIM
            screen.blit(self._font_row.render(
                f"{box}  {display_name(entry, self._mc_catalog)}", True, col),
                (r.x + 12, r.y + 7))
            screen.blit(self._font_hint.render(f"x{entry.qty}", True, MUTED),
                        (r.right - 50, r.y + 11))
        render_hint(screen, self._font_hint,
                    "UP/DOWN move   SPACE toggle   ESC done",
                    cx, modal.bottom - 32)

    # ── Edit Tags modal ───────────────────────────────────────

    def _draw_tags_modal(self, screen, entry, rows, sel, warning) -> None:
        if not entry:
            return
        mw, mh = 420, 380
        modal = render_modal(screen, mw, mh)
        ox, oy = modal.x, modal.y
        cx, cy = ox + 16, oy + 14
        screen.blit(self._font_title.render(
            f"Edit Tags: {entry.name or entry.id}", True, GOLD), (cx, cy))
        cy += self._font_title.get_height() + 8
        draw_divider(screen, cx, cy, mw - 32)
        cy += 10

        last_section = None
        for i, row in enumerate(rows):
            kind, tag = row
            section = ("System Tags" if kind == "system" else
                       "Custom Tags" if kind in ("custom", "new") else None)
            if section and section != last_section:
                if last_section is not None:
                    cy += 6
                lbl = self._font_hint.render(section, True, MUTED)
                screen.blit(lbl, (cx, cy))
                cy += lbl.get_height() + 4
                last_section = section
            row_h = 26
            if i == sel:
                render_row_frame(screen,
                                 pygame.Rect(cx - 4, cy - 2, mw - 28, row_h),
                                 focused=True)
            if kind == "new":
                label, col = "[+] New Tag...", INK
            else:
                checked = tag in entry.tags
                label = f"{'[x]' if checked else '[ ]'} {tag}"
                col = INK if checked else MUTED
            screen.blit(self._font_meta.render(label, True, col), (cx + 4, cy + 2))
            cy += row_h

        cy = oy + mh - 56
        draw_divider(screen, cx, cy, mw - 32)
        cy += 6
        screen.blit(self._font_hint.render(
            f"Tags: {len(entry.tags)}/5", True, MUTED), (cx, cy))
        if warning:
            warn = self._font_hint.render(warning, True, EMBER)
            screen.blit(warn, (ox + mw - 16 - warn.get_width(), cy))
        cy += 18
        screen.blit(self._font_hint.render(
            "ENTER toggle   ESC back", True, DIM), (cx, cy))

    def _draw_new_tag_modal(self, screen, text) -> None:
        mw, mh = 360, 110
        modal = render_modal(screen, mw, mh)
        ox, oy = modal.x, modal.y
        cx, cy = ox + 16, oy + 14
        screen.blit(self._font_title.render("New Tag", True, GOLD), (cx, cy))
        cy += self._font_title.get_height() + 6
        box = pygame.Rect(cx, cy, mw - 32, 28)
        pygame.draw.rect(screen, (12, 12, 16), box, border_radius=4)
        pygame.draw.rect(screen, BORDER_ACTIVE, box, 1, border_radius=4)
        screen.blit(self._font_meta.render(text + "|", True, INK),
                    (cx + 6, cy + (28 - self._font_meta.get_height()) // 2))
        cy += 34
        render_hint(screen, self._font_hint, "ENTER confirm   ESC cancel", cx, cy)


def _short_desc(entry: ItemEntry) -> str:
    return entry.description or ""
