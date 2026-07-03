# engine/status/status_renderer.py
#
# Drawing for the Status screen — panels, portrait, lore, stat bars,
# spell/position lists, hints. StatusScene owns input/flow and passes a
# per-frame view of its state; this class owns fonts, layout constants,
# and the portrait scale cache (follows the battle renderer split).

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.color_constants import C_TEXT_DIM, HP_LOW_THRESHOLD
from engine.common.font_provider import FontSet
from engine.common.font_roles import CAPTION
from engine.common.member_card import CARD_COLUMN_EXTRA, member_column_width, render_member_column
from engine.common.menu_popup import render_popup
from engine.common.ui.chrome import (
    draw_divider,
    fit_text,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    wrap_text,
)
from engine.common.ui.image_cache import load_image
from engine.common.ui.theme import (
    DIM,
    GOLD,
    INK,
    MUTED,
    TEAL,
    VIOLET,
    member_icon_path,
    theme_asset_root,
)
from engine.party.member_state import MemberState
from engine.party.party_state import exp_pct
from engine.spell.spell_logic import is_field_castable

# Flow pages (owned by the scene, shared here for panel focus states)
PAGE_MEMBER   = "member"
PAGE_CATEGORY = "category"
PAGE_DETAIL   = "detail"

CAT_SPELLS   = "spells"
CAT_POSITION = "position"
CATEGORIES: tuple[tuple[str, str], ...] = (
    (CAT_SPELLS,   "Spells"),
    (CAT_POSITION, "Position"),
)

ROWS: tuple[tuple[str, str], ...] = (("front", "Front"), ("back", "Back"))

STAT_ORDER = (("str", "STR"), ("dex", "DEX"), ("con", "CON"), ("int", "INT"))
GEAR_ORDER = (
    ("weapon", "Wpn"), ("shield", "Shld"), ("helmet", "Helm"),
    ("body", "Body"), ("accessory", "Acc"),
)
MEMBER_LORE: dict[str, dict[str, str]] = {
    "aric": {
        "meta": "17 / Male / Hero",
        "persona": "Earnest, burdened, and stubbornly humane. Aric doubts the role forced onto him, but not the people walking beside him.",
        "backstory": "Found as an infant at Ardel's shrine, swaddled in ash, Aric grew up as a village smith's apprentice. When the forest rusted and Ardel was attacked, the ember he had hidden since childhood became a true flame.",
        "argument": "Restoration tested by conscience.",
    },
    "elise": {
        "meta": "16 / Female / Cleric",
        "persona": "Skeptical, precise, and compassionate in ways she rarely announces. Elise trusts evidence first, but she keeps asking questions because she still cares about the answers.",
        "backstory": "A traveling scholar chasing forbidden records of the old Flame, Elise reaches Ardel already one step ahead of the official story. Her research turns Aric's private mystery into a road north.",
        "argument": "Knowing, even when knowledge wounds.",
    },
    "reiya": {
        "meta": "18 / Female / Sorcerer",
        "persona": "Quietly intense, devout without obedience, and unwilling to look away from suffering. Reiya does not serve Aric; she bears witness.",
        "backstory": "A priestess-in-exile tending the quarantined sick against guild orders, Reiya is the first to name Aric's power as a Vessel-flame. Her order was destroyed for teaching the same doctrine.",
        "argument": "Witnessing what others bury.",
    },
    "jep": {
        "meta": "15 / Male Halfling / Rogue",
        "persona": "A wary halfling survivor with quick eyes, quick hands, and little patience for noble speeches. Jep endures by reading danger before anyone else admits it is there.",
        "backstory": "Once hired to silence anyone prying into Millhaven's stolen Flame fragment, Jep turns on his employers after recognizing Aric's fire from a battlefield massacre he survived and never speaks of plainly.",
        "argument": "Enduring without surrendering.",
    },
    "kael": {
        "meta": "20 / Male / Warrior",
        "persona": "Stern, oathbound, and protective. Kael carries faith like armor: dented, heavy, and still deliberately worn.",
        "backstory": "The last sworn sword of a disbanded order, Kael hunts the Cinder Marshal through Ruinwatch's dead monastery. After saving Aric from the Marshal, the oath shifts from a dead saint to the road ahead.",
        "argument": "Keeping faith after institutions fail.",
    },
}

PAD_X = 40
PAD_Y = 30
GAP = 18
ROW_H = 54
BAR_H = 10

HP_BAR_OK  = (132, 196, 111)
HP_BAR_LOW = (203, 82, 47)
BAR_TRACK  = (17, 17, 22)


class StatusRenderer:
    def __init__(self) -> None:
        self._fonts = FontSet(
            title=(24, True), head=(18, True), row=18, stat=16,
            meta=CAPTION, hint=14, small=CAPTION,
        )
        # Portraits scaled to a panel size, keyed by (member id, panel w, h)
        # — avoids a per-frame copy + smoothscale in the render loop.
        self._portrait_cache: dict[tuple[str, int, int], pygame.Surface] = {}

    # ── Main entry point ──────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        *,
        page_id: str,
        members: list[MemberState],
        member: MemberState | None,
        member_selection: int,
        category_selection: int,
        detail_selection: int,
        detail_mode: str,
        spells: list[dict],
        display_name,          # callable(item_id) -> str
    ) -> None:
        render_backdrop(screen)
        render_header(screen, self._fonts.title, self._fonts.hint,
                      "STATUS", "party roster and growth", PAD_X, PAD_Y)

        member_rect, detail_rect, action_rect = self._layout(screen)
        render_panel(screen, member_rect, active=page_id == PAGE_MEMBER,
                     title="Party", title_font=self._fonts.head)
        self._render_members(screen, member_rect, members, member_selection, page_id)

        if page_id == PAGE_MEMBER and member is not None:
            render_panel(screen, detail_rect)
            self._render_portrait_panel(screen, detail_rect, member)
            render_panel(screen, action_rect, title="Persona", title_font=self._fonts.head)
            self._render_lore_panel(screen, action_rect, member)
        elif page_id in (PAGE_CATEGORY, PAGE_DETAIL) and member is not None:
            render_panel(screen, detail_rect, active=page_id == PAGE_CATEGORY,
                         title=member.name, title_font=self._fonts.head)
            self._render_detail_panel(
                screen, detail_rect, member,
                display_name=display_name,
                category_selection=category_selection,
                page_id=page_id,
            )
            if page_id == PAGE_CATEGORY:
                render_panel(screen, action_rect, title="Persona", title_font=self._fonts.head)
                self._render_lore_panel(screen, action_rect, member)
        if page_id == PAGE_DETAIL and member is not None:
            title = "Spells" if detail_mode == CAT_SPELLS else "Position"
            render_panel(screen, action_rect, active=True,
                         title=title, title_font=self._fonts.head)
            if detail_mode == CAT_SPELLS:
                self._render_spells(screen, action_rect, member, spells, detail_selection)
            else:
                self._render_position(screen, action_rect, member, detail_selection)

        self._render_hint(screen, page_id, detail_mode)

    def render_popup(self, screen: pygame.Surface, text: str) -> None:
        """Drawn last by the scene so it sits above any overlay."""
        render_popup(screen, self._fonts.row, self._fonts.meta, text)

    # ── Layout ────────────────────────────────────────────────

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        panel_h = max(360, sh - top - 62)
        available = sw - PAD_X * 2 - GAP * 2
        member_w = member_column_width(sw)
        # Portrait column (col 2) keeps its pre-widening budget; the extra card
        # width is reclaimed from the lore column (col 3) so margins hold.
        remaining = available - (member_w - CARD_COLUMN_EXTRA)
        detail_w = remaining // 2
        action_w = remaining - detail_w - CARD_COLUMN_EXTRA
        member_rect = pygame.Rect(PAD_X, top, member_w, panel_h)
        detail_rect = pygame.Rect(member_rect.right + GAP, top, detail_w, panel_h)
        action_rect = pygame.Rect(detail_rect.right + GAP, top, action_w, panel_h)
        return member_rect, detail_rect, action_rect

    # ── Col 1: party cards (matches the equipment party panel) ─

    def _render_members(
        self, screen: pygame.Surface, panel: pygame.Rect,
        members: list[MemberState], selection: int, page_id: str,
    ) -> None:
        render_member_column(
            screen, panel, members,
            selection=selection,
            active_page=page_id == PAGE_MEMBER,
            font_head=self._fonts.head,
            font_row=self._fonts.row,
            font_meta=self._fonts.meta,
        )

    # ── Col 2: member detail + action menu ────────────────────

    def _render_portrait_panel(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        cache_key = (m.id, panel.w, panel.h)
        portrait = self._portrait_cache.get(cache_key)
        if portrait is None:
            image_path = _status_portrait_path(m.id)
            image = load_image(image_path) if image_path is not None else None
            if image is None:
                msg = self._fonts.row.render("No portrait.", True, C_TEXT_DIM)
                screen.blit(msg, (panel.centerx - msg.get_width() // 2, panel.centery))
                return
            portrait = image
            if portrait.get_width() > panel.w - 14 or portrait.get_height() > panel.h - 12:
                max_w = panel.w - 14
                max_h = panel.h - 12
                scale = min(max_w / portrait.get_width(), max_h / portrait.get_height())
                size = (
                    max(1, int(portrait.get_width() * scale)),
                    max(1, int(portrait.get_height() * scale)),
                )
                portrait = pygame.transform.smoothscale(portrait, size)
            self._portrait_cache[cache_key] = portrait

        frame = portrait.get_rect(center=panel.center).inflate(10, 10)
        pygame.draw.rect(screen, (8, 8, 12, 190), frame, border_radius=5)
        pygame.draw.rect(screen, GOLD, frame, width=1, border_radius=5)
        screen.blit(portrait, portrait.get_rect(center=frame.center))

    def _render_lore_panel(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        lore = MEMBER_LORE.get(m.id, {})
        x = panel.x + 18
        y = panel.y + 52
        w = panel.w - 36

        meta = lore.get("meta", m.class_name.title())
        screen.blit(self._fonts.meta.render(meta, True, MUTED), (x, y))
        y += self._fonts.meta.get_height() + 18

        y = self._render_lore_section(screen, x, y, w, "Persona", lore.get("persona", ""))
        y += 12
        y = self._render_lore_section(screen, x, y, w, "Backstory", lore.get("backstory", ""))
        argument = lore.get("argument", "")
        if argument and y < panel.bottom - 72:
            draw_divider(screen, x, y + 4, w)
            y += 18
            screen.blit(self._fonts.meta.render("Throughline", True, GOLD), (x, y))
            y += self._fonts.meta.get_height() + 5
            for line in wrap_text(self._fonts.small, argument, w, limit=3):
                screen.blit(self._fonts.small.render(line, True, MUTED), (x, y))
                y += self._fonts.small.get_height() + 3

    def _render_lore_section(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        w: int,
        label: str,
        text: str,
    ) -> int:
        screen.blit(self._fonts.meta.render(label, True, GOLD), (x, y))
        y += self._fonts.meta.get_height() + 5
        if not text:
            text = "No record."
        for line in wrap_text(self._fonts.small, text, w, limit=7):
            screen.blit(self._fonts.small.render(line, True, INK), (x, y))
            y += self._fonts.small.get_height() + 3
        return y

    def _render_detail_panel(
        self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState,
        *, display_name, category_selection: int, page_id: str,
    ) -> None:
        x = panel.x + 18
        w = panel.w - 36
        y = panel.y + 52

        # Level + EXP
        screen.blit(self._fonts.stat.render(f"Lv {m.level}", True, INK), (x, y))
        exp_txt = self._fonts.meta.render(f"EXP {m.exp}/{m.exp_next}", True, MUTED)
        screen.blit(exp_txt, (panel.right - 18 - exp_txt.get_width(), y + 2))
        y += self._fonts.stat.get_height() + 6
        self._bar(screen, x, y, w, exp_pct(m), VIOLET)
        y += BAR_H + 14

        # HP / MP bars
        hp_pct = m.hp / m.hp_max if m.hp_max > 0 else 0
        hp_col = HP_BAR_LOW if hp_pct < HP_LOW_THRESHOLD else HP_BAR_OK
        y = self._stat_bar_row(screen, x, y, w, "HP", f"{m.hp}/{m.hp_max}", hp_pct, hp_col)
        if m.mp_max > 0:
            y = self._stat_bar_row(screen, x, y, w, "MP", f"{m.mp}/{m.mp_max}", m.mp / m.mp_max, TEAL)
        else:
            screen.blit(self._fonts.meta.render("MP  -", True, DIM), (x, y))
            y += self._fonts.meta.get_height() + BAR_H + 6
        y += 6

        # Stats grid (2 columns)
        col2_x = x + w // 2
        line_h = self._fonts.stat.get_height() + 8
        stat_vals = {"str": m.str_, "dex": m.dex, "con": m.con, "int": m.int_}
        for i, (key, label) in enumerate(STAT_ORDER):
            cx = x if i % 2 == 0 else col2_x
            cy = y + (i // 2) * line_h
            screen.blit(self._fonts.meta.render(label, True, MUTED), (cx, cy))
            screen.blit(self._fonts.stat.render(str(stat_vals[key]), True, INK), (cx + 42, cy - 1))
        y += 2 * line_h + 6

        # Gear
        for slot, label in GEAR_ORDER:
            item_id = m.equipped.get(slot)
            val = display_name(item_id) if item_id else "-"
            screen.blit(self._fonts.meta.render(label, True, MUTED), (x, y))
            screen.blit(fit_text(self._fonts.meta, val,
                                 INK if item_id else DIM, w - 48), (x + 48, y))
            y += self._fonts.meta.get_height() + 4

        # Action menu, anchored to the bottom of the panel
        self._render_category_menu(screen, panel, m, category_selection, page_id)

    def _render_category_menu(
        self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState,
        selection: int, page_id: str,
    ) -> None:
        x = panel.x + 16
        w = panel.w - 32
        menu_h = len(CATEGORIES) * (ROW_H + 8)
        y = panel.bottom - 18 - menu_h
        draw_divider(screen, x, y - 12, w)

        on_category = page_id == PAGE_CATEGORY
        for i, (key, label) in enumerate(CATEGORIES):
            selected = (i == selection)
            right = m.row.title() if key == CAT_POSITION else ""
            rect = pygame.Rect(x, y + i * (ROW_H + 8), w, ROW_H)
            render_icon_row(
                screen, self._fonts.row, rect, label,
                icon_key=f"cat_{key}",
                focused=selected and on_category,
                dimmed_sel=selected and page_id == PAGE_DETAIL,
                color=INK,
                right_text=right,
                right_font=self._fonts.meta,
            )

    # ── Col 3: spells or position ─────────────────────────────

    def _render_spells(
        self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState,
        spells: list[dict], selection: int,
    ) -> None:
        x = panel.x + 16
        y = panel.y + 52
        w = panel.w - 32
        if not spells:
            screen.blit(self._fonts.row.render("No spells learned.", True, DIM), (x, y))
            return
        for i, spell in enumerate(spells):
            selected = (i == selection)
            castable = is_field_castable(spell)
            can_afford = m.mp >= spell["mp_cost"]
            if castable and can_afford:
                color = INK
            elif castable:
                color = MUTED
            else:
                color = DIM
            badge = "field cast" if castable else "battle only"
            rect = pygame.Rect(x, y + i * (ROW_H + 8), w, ROW_H)
            render_icon_row(
                screen, self._fonts.row, rect, spell["name"],
                icon_key=_spell_icon_key(spell),
                focused=selected,
                dimmed_sel=False,
                color=color,
                right_text=f"MP {spell['mp_cost']}",
                right_font=self._fonts.meta,
                subtext=f"{badge} / {spell.get('target', 'self')}",
                sub_font=self._fonts.small,
            )

        spell = spells[selection]
        desc = spell.get("description", "")
        if desc:
            dy = panel.bottom - 70
            draw_divider(screen, x, dy - 10, w)
            for line in wrap_text(self._fonts.meta, desc, w, limit=3):
                screen.blit(self._fonts.meta.render(line, True, MUTED), (x, dy))
                dy += self._fonts.meta.get_height() + 3

    def _render_position(
        self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState, selection: int,
    ) -> None:
        x = panel.x + 16
        y = panel.y + 52
        w = panel.w - 32
        for i, (key, label) in enumerate(ROWS):
            selected = (i == selection)
            current = (m.row == key)
            rect = pygame.Rect(x, y + i * (ROW_H + 8), w, ROW_H)
            render_icon_row(
                screen, self._fonts.row, rect, label,
                icon_key=f"row_{key}",
                focused=selected,
                dimmed_sel=False,
                color=INK,
                right_text="current" if current else "",
                right_font=self._fonts.meta,
            )

    # ── Shared bar helpers ────────────────────────────────────

    def _bar(self, screen, x, y, w, pct, color) -> None:
        pygame.draw.rect(screen, BAR_TRACK, (x, y, w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, color, (x, y, int(w * max(0.0, min(1.0, pct))), BAR_H), border_radius=3)

    def _stat_bar_row(self, screen, x, y, w, label, value, pct, color) -> int:
        lbl = self._fonts.meta.render(label, True, color)
        val = self._fonts.meta.render(value, True, MUTED)
        screen.blit(lbl, (x, y))
        screen.blit(val, (x + w - val.get_width(), y))
        bar_y = y + lbl.get_height() + 2
        self._bar(screen, x, bar_y, w, pct, color)
        return bar_y + BAR_H + 8

    # ── Hint ──────────────────────────────────────────────────

    def _render_hint(self, screen: pygame.Surface, page_id: str, detail_mode: str) -> None:
        sw, sh = screen.get_size()
        if page_id == PAGE_MEMBER:
            text = "UP/DOWN select member    ENTER stats    ESC close"
        elif page_id == PAGE_CATEGORY:
            text = "UP/DOWN select    ENTER open    ESC back"
        elif detail_mode == CAT_SPELLS:
            text = "UP/DOWN select spell    ENTER cast    ESC back"
        else:
            text = "UP/DOWN select row    ENTER set    ESC back"
        hint = self._fonts.hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))


def _spell_icon_key(spell: dict) -> str:
    if spell.get("warp"):
        return "spell_warp"
    element = spell.get("element")
    if element:
        return f"spell_{element}"
    return f"spell_{spell.get('type', 'utility')}"


def _status_portrait_path(member_id: str) -> Path | None:
    portrait_dir = theme_asset_root() / "images" / "party_portraits_large"
    path = portrait_dir / f"{member_id}_status_portrait.webp"
    if path.exists():
        return path
    return member_icon_path(member_id)
