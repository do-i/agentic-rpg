# engine/core/scenes/item_scene.py

from __future__ import annotations

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.repository_state import ItemEntry, RepositoryState

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

DETAIL_BG       = (32, 32, 54)
DETAIL_BDR      = (55, 55, 80)

BTN_BG          = (55, 45, 80)
BTN_BG_HOV      = (75, 60, 110)
BTN_BG_DIS      = (38, 38, 55)
BTN_BDR         = (130, 100, 180)
BTN_BDR_DIS     = (55, 55, 70)
BTN_TEXT        = (220, 200, 255)
BTN_TEXT_DIS    = (80, 80, 95)

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

# ── Tabs ──────────────────────────────────────────────────────
TABS = ["New", "All", "Recovery", "Status", "Battle", "Material", "Key"]

# Item type → tab mapping
TYPE_TO_TAB: dict[str, str] = {
    "consumable": "",   # resolved by use_context/effect below — see _item_tab()
    "material":   "Material",
    "key":        "Key",
}


def _item_tab(entry: ItemEntry) -> str:
    """Derive display tab from item metadata stub."""
    # In the real engine this reads from item master; for the stub we use tags.
    tags = entry.tags
    if "key" in tags:
        return "Key"
    if "material" in tags:
        return "Material"
    if "battle" in tags and "consumable" not in tags:
        return "Battle"
    if "status" in tags:
        return "Status"
    if "consumable" in tags or "recovery" in tags:
        return "Recovery"
    return "All"


# ── Debug stub data ───────────────────────────────────────────
def _make_debug_repository() -> RepositoryState:
    r = RepositoryState(gp=3200)

    items = [
        # id, qty, tags, description, locked, acq_order
        ("potion",        5,  {"consumable", "recovery"},  "Restores 100 HP to one ally.",                   False),
        ("hi_potion",     3,  {"consumable", "recovery"},  "Restores 500 HP to one ally.",                   False),
        ("elixir",        1,  {"consumable", "recovery"},  "Fully restores HP and MP of one ally.",          True),
        ("ether",         2,  {"consumable", "recovery"},  "Restores 50 MP to one ally.",                    False),
        ("antidote",      4,  {"consumable", "status"},    "Cures poison from one ally.",                    False),
        ("echo_herb",     2,  {"consumable", "status"},    "Cures silence from one ally.",                   False),
        ("remedy",        1,  {"consumable", "status"},    "Cures poison, silence, and sleep.",              False),
        ("fire_vial",     3,  {"battle"},                  "Deals 150 fire damage to one enemy.",            False),
        ("holy_water",    2,  {"battle"},                  "Deals 200 holy damage. Bonus vs undead/demon.",  False),
        ("tent",          2,  {"consumable", "recovery"},  "Restores HP and MP of all allies on world map.", False),
        ("wolf_fang",     6,  {"material"},                "A sharp fang. Used in crafting.",                False),
        ("spider_silk",   4,  {"material"},                "Fine silk thread. Used in crafting.",            False),
        ("venom_sac",     3,  {"material"},                "A sac filled with venom. Used in crafting.",     False),
        ("rare_herb",     2,  {"material"},                "A rare medicinal herb. Used in crafting.",       False),
        ("phoenix_wing",  1,  {"key"},                     "Revives a fallen ally on the world map. Never consumed.", True),
        ("veil_breaker",  1,  {"consumable", "battle"},    "Allows attacks to reach barrier-type enemies.",  False),
    ]

    for item_id, qty, tags, desc, locked in items:
        r.add_item(item_id, qty)
        entry = r.get_item(item_id)
        entry.tags = tags
        entry.locked = locked
        entry.description = desc  # type: ignore[attr-defined]

    return r


class ItemScene(Scene):
    """
    Party repository item screen.
    I / ESC to close. Tab left/right with Q/E. Up/Down navigate list.
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

        self._tab_index: int = 0          # index into TABS
        self._list_sel: int = 0           # selected row in current filtered list
        self._scroll: int = 0             # scroll offset
        self._action_sel: int = 0         # 0 = Use/first btn, 1 = Discard
        self._in_action: bool = False     # focus on action buttons?
        self._confirm_discard: bool = False

        self._fonts_ready = False
        self._debug_repo = _make_debug_repository()

    # ── Font init ─────────────────────────────────────────────

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

    # ── Data helpers ──────────────────────────────────────────

    def _get_repo(self) -> RepositoryState:
        # Use debug repo until Phase 6 wires real repository
        return self._debug_repo

    def _filtered_items(self) -> list[ItemEntry]:
        repo = self._get_repo()
        all_items = repo.items
        tab = TABS[self._tab_index]

        if tab == "New":
            # acquisition order (list order), newest first
            return list(reversed(all_items))
        if tab == "All":
            return sorted(all_items, key=lambda e: e.id)

        # category filter + alphabetical
        def matches(e: ItemEntry) -> bool:
            tags = e.tags
            if tab == "Recovery":
                return "recovery" in tags or ("consumable" in tags and "status" not in tags
                                               and "battle" not in tags and "key" not in tags
                                               and "material" not in tags)
            if tab == "Status":
                return "status" in tags
            if tab == "Battle":
                return "battle" in tags
            if tab == "Material":
                return "material" in tags
            if tab == "Key":
                return "key" in tags
            return True

        return sorted(filter(matches, all_items), key=lambda e: e.id)

    def _selected_entry(self) -> ItemEntry | None:
        items = self._filtered_items()
        if not items:
            return None
        idx = min(self._list_sel, len(items) - 1)
        return items[idx]

    def _is_new(self, entry: ItemEntry) -> bool:
        return "new" in entry.tags

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self._confirm_discard:
                self._handle_confirm(event.key)
                return

            if event.key in (pygame.K_i, pygame.K_ESCAPE):
                self._close()
            elif event.key == pygame.K_q:
                self._change_tab(-1)
            elif event.key == pygame.K_e:
                self._change_tab(1)
            elif not self._in_action:
                self._handle_list_key(event.key)
            else:
                self._handle_action_key(event.key)

    def _close(self) -> None:
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    def _change_tab(self, delta: int) -> None:
        self._tab_index = (self._tab_index + delta) % len(TABS)
        self._list_sel = 0
        self._scroll = 0
        self._in_action = False
        self._confirm_discard = False

    def _handle_list_key(self, key: int) -> None:
        items = self._filtered_items()
        if not items:
            return
        if key == pygame.K_UP:
            self._list_sel = max(0, self._list_sel - 1)
            self._clamp_scroll()
        elif key == pygame.K_DOWN:
            self._list_sel = min(len(items) - 1, self._list_sel + 1)
            self._clamp_scroll()
        elif key in (pygame.K_RETURN, pygame.K_RIGHT):
            self._in_action = True
            self._action_sel = 0

    def _handle_action_key(self, key: int) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        actions = self._actions_for(entry)
        if key == pygame.K_LEFT or key == pygame.K_ESCAPE:
            self._in_action = False
        elif key == pygame.K_UP:
            self._action_sel = max(0, self._action_sel - 1)
        elif key == pygame.K_DOWN:
            self._action_sel = min(len(actions) - 1, self._action_sel + 1)
        elif key == pygame.K_RETURN:
            label = actions[self._action_sel]
            if label == "Discard" and not entry.locked:
                self._confirm_discard = True

    def _handle_confirm(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_y):
            entry = self._selected_entry()
            if entry:
                repo = self._get_repo()
                repo._items.pop(entry.id, None)
                items = self._filtered_items()
                self._list_sel = min(self._list_sel, max(0, len(items) - 1))
            self._confirm_discard = False
            self._in_action = False
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            self._confirm_discard = False

    def _clamp_scroll(self) -> None:
        if self._list_sel < self._scroll:
            self._scroll = self._list_sel
        elif self._list_sel >= self._scroll + VISIBLE_ROWS:
            self._scroll = self._list_sel - VISIBLE_ROWS + 1

    def _actions_for(self, entry: ItemEntry) -> list[str]:
        tags = entry.tags
        actions = []
        if "key" not in tags and "material" not in tags:
            actions.append("Use")
        if not entry.locked:
            actions.append("Discard")
        return actions or ["—"]

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(BG_COLOR)

        self._draw_header(screen)
        self._draw_tabs(screen)

        # Panel layout
        panel_top    = PAD + HEADER_H + TAB_H + TAB_GAP * 2
        panel_bottom = Settings.SCREEN_HEIGHT - FOOTER_H - PAD
        panel_h      = panel_bottom - panel_top

        list_x  = PAD
        det_x   = PAD + LIST_W + PAD
        det_w   = Settings.SCREEN_WIDTH - det_x - PAD

        self._draw_list_panel(screen, list_x, panel_top, LIST_W, panel_h)
        self._draw_detail_panel(screen, det_x, panel_top, det_w, panel_h)
        self._draw_footer(screen)

        if self._confirm_discard:
            self._draw_confirm_overlay(screen)

    # ── Header ────────────────────────────────────────────────

    def _draw_header(self, screen: pygame.Surface) -> None:
        title = self._font_title.render("ITEMS", True, HEADER_COLOR)
        screen.blit(title, (PAD, PAD + 6))

        repo = self._get_repo()
        gp_val   = self._font_gp.render(f"{repo.gp}", True, TEXT_PRIMARY)
        gp_label = self._font_gp.render("GP", True, HEADER_COLOR)
        gx = Settings.SCREEN_WIDTH - PAD - gp_val.get_width()
        screen.blit(gp_val,   (gx, PAD + 6))
        screen.blit(gp_label, (gx - gp_label.get_width() - 6, PAD + 6))

        pygame.draw.line(screen, DIVIDER,
                         (PAD, PAD + HEADER_H - 2),
                         (Settings.SCREEN_WIDTH - PAD, PAD + HEADER_H - 2))

    # ── Tabs ──────────────────────────────────────────────────

    def _draw_tabs(self, screen: pygame.Surface) -> None:
        tab_y = PAD + HEADER_H + TAB_GAP
        x = PAD
        for i, label in enumerate(TABS):
            active = (i == self._tab_index)
            # measure width
            surf = self._font_tab.render(label, True, TEXT_PRIMARY)
            tw = surf.get_width() + 24
            bg  = TAB_BG_ACT  if active else TAB_BG_NORM
            bdr = TAB_BORDER_ACT if active else TAB_BORDER_NORM
            pygame.draw.rect(screen, bg,  (x, tab_y, tw, TAB_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (x, tab_y, tw, TAB_H), 1, border_radius=4)
            col = HEADER_COLOR if active else TEXT_SECONDARY
            txt = self._font_tab.render(label, True, col)
            screen.blit(txt, (x + 12, tab_y + (TAB_H - txt.get_height()) // 2))
            x += tw + TAB_GAP

    # ── List panel ────────────────────────────────────────────

    def _draw_list_panel(self, screen: pygame.Surface,
                         x: int, y: int, w: int, h: int) -> None:
        pygame.draw.rect(screen, LIST_BG, (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, DIVIDER, (x, y, w, h), 1, border_radius=6)

        items = self._filtered_items()
        tab   = TABS[self._tab_index]

        if not items:
            empty = self._font_detail.render("No items.", True, TEXT_DIM)
            screen.blit(empty, (x + 16, y + 16))
            return

        row_y = y + 6
        for i in range(VISIBLE_ROWS):
            idx = self._scroll + i
            if idx >= len(items):
                break
            entry   = items[idx]
            sel     = (idx == self._list_sel)
            row_x   = x + 6
            row_w   = w - 12

            if sel:
                pygame.draw.rect(screen, LIST_SEL_BG,  (row_x, row_y, row_w, ITEM_ROW_H), border_radius=4)
                pygame.draw.rect(screen, LIST_SEL_BDR, (row_x, row_y, row_w, ITEM_ROW_H), 1, border_radius=4)
            else:
                pygame.draw.rect(screen, LIST_NORM_BDR, (row_x, row_y, row_w, ITEM_ROW_H), 1, border_radius=4)

            # cursor
            if sel and not self._in_action:
                cur = self._font_item.render("▶", True, HEADER_COLOR)
                screen.blit(cur, (row_x + 4, row_y + (ITEM_ROW_H - cur.get_height()) // 2))

            # NEW badge (tab == New, first few or tagged)
            badge_x = row_x + 20
            if tab == "New" and idx < 3:
                badge = self._font_new.render("NEW", True, TEXT_NEW)
                screen.blit(badge, (badge_x, row_y + (ITEM_ROW_H - badge.get_height()) // 2))
                badge_x += badge.get_width() + 6

            # item name
            name = entry.id.replace("_", " ").title()
            locked_marker = " 🔒" if entry.locked else ""
            name_col = TEXT_DIM if entry.locked else (TEXT_PRIMARY if sel else TEXT_SECONDARY)
            name_surf = self._font_item.render(name + locked_marker, True, name_col)
            screen.blit(name_surf, (badge_x, row_y + (ITEM_ROW_H - name_surf.get_height()) // 2))

            # quantity
            qty_surf = self._font_qty.render(f"× {entry.qty}", True, HEADER_COLOR if sel else MUTED)
            screen.blit(qty_surf, (row_x + row_w - qty_surf.get_width() - 10,
                                   row_y + (ITEM_ROW_H - qty_surf.get_height()) // 2))

            row_y += ITEM_ROW_H + ITEM_ROW_GAP

        # scroll indicators
        if self._scroll > 0:
            up = self._font_hint.render("▲", True, MUTED)
            screen.blit(up, (x + w - up.get_width() - 8, y + 4))
        if self._scroll + VISIBLE_ROWS < len(items):
            dn = self._font_hint.render("▼", True, MUTED)
            screen.blit(dn, (x + w - dn.get_width() - 8, y + h - dn.get_height() - 4))

    # ── Detail panel ──────────────────────────────────────────

    def _draw_detail_panel(self, screen: pygame.Surface,
                           x: int, y: int, w: int, h: int) -> None:
        pygame.draw.rect(screen, DETAIL_BG, (x, y, w, h), border_radius=6)
        pygame.draw.rect(screen, DETAIL_BDR, (x, y, w, h), 1, border_radius=6)

        entry = self._selected_entry()
        if not entry:
            return

        cx = x + 16
        cy = y + 16

        # Item name
        name = entry.id.replace("_", " ").title()
        name_surf = self._font_title.render(name, True, HEADER_COLOR)
        screen.blit(name_surf, (cx, cy))
        cy += name_surf.get_height() + 4

        # Quantity
        qty_surf = self._font_detail.render(f"Quantity:  {entry.qty}", True, TEXT_SECONDARY)
        screen.blit(qty_surf, (cx, cy))
        cy += qty_surf.get_height() + 14

        # Divider
        pygame.draw.line(screen, DIVIDER, (cx, cy), (x + w - 16, cy))
        cy += 12

        # Description
        desc = getattr(entry, "description", "No description available.")
        cy = self._draw_wrapped(screen, desc, cx, cy, w - 32, TEXT_PRIMARY)
        cy += 20

        # Tags
        if entry.tags:
            tag_str = "  ".join(f"[{t}]" for t in sorted(entry.tags))
            tag_surf = self._font_hint.render(tag_str, True, MUTED)
            screen.blit(tag_surf, (cx, cy))
            cy += tag_surf.get_height() + 20

        # Divider
        pygame.draw.line(screen, DIVIDER, (cx, cy), (x + w - 16, cy))
        cy += 16

        # Action buttons
        actions = self._actions_for(entry)
        for i, label in enumerate(actions):
            is_sel   = self._in_action and (i == self._action_sel)
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
        words = text.split()
        line, line_y = "", y
        lh = self._font_detail.get_height() + 3
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

    # ── Confirm overlay ───────────────────────────────────────

    def _draw_confirm_overlay(self, screen: pygame.Surface) -> None:
        entry = self._selected_entry()
        name  = entry.id.replace("_", " ").title() if entry else "item"

        ow, oh = 420, 110
        ox = (Settings.SCREEN_WIDTH  - ow) // 2
        oy = (Settings.SCREEN_HEIGHT - oh) // 2
        pygame.draw.rect(screen, (30, 15, 20), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, (180, 70, 70), (ox, oy, ow, oh), 2, border_radius=6)

        msg  = self._font_detail.render(f"Discard {name}?", True, (220, 180, 180))
        hint = self._font_hint.render("ENTER / Y — Confirm    ESC / N — Cancel", True, (160, 120, 120))
        screen.blit(msg,  (ox + 20, oy + 18))
        screen.blit(hint, (ox + 20, oy + 58))

    # ── Footer ────────────────────────────────────────────────

    def _draw_footer(self, screen: pygame.Surface) -> None:
        fy = Settings.SCREEN_HEIGHT - FOOTER_H
        pygame.draw.line(screen, DIVIDER, (PAD, fy), (Settings.SCREEN_WIDTH - PAD, fy))
        hint = self._font_hint.render(
            "↑↓ navigate · Q/E tab · → actions · I close", True, MUTED)
        screen.blit(hint, (PAD, fy + 8))