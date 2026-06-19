# engine/status/status_scene.py
#
# Field Status screen: party → member detail → action. Built on
# engine.common.wizard_scene so navigation, hover SFX, and the scene-close
# path are shared with EquipScene / SpellScene.
#
# Pages:
#   MEMBER   (col 1) — party roster cards; col 2 shows the selected portrait,
#                      col 3 shows backstory/persona.
#   CATEGORY (col 2) — selected member's detailed stats, plus a small action
#                      menu (Spells / Position), shown after ENTER.
#   DETAIL   (col 3) — content of the chosen action:
#                        Spells   → learned spells; field-castable ones cast
#                                   (heal/buff via target overlay, teleport via
#                                   warp picker), battle-only are inspect-only.
#                        Position → set the member's battle row (front/back).

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.color_constants import C_TEXT_DIM, HP_LOW_THRESHOLD
from engine.common.font_roles import CAPTION
from engine.common.field_menu_theme import (
    ASSET_ROOT,
    DIM,
    GOLD,
    INK,
    MUTED,
    TEAL,
    VIOLET,
    draw_divider,
    fit_text,
    icon_surface,
    load_image,
    member_icon_path,
    render_backdrop,
    render_header,
    render_icon_row,
    render_panel,
    render_row_frame,
    wrap_text,
)
from engine.common.menu_popup import render_popup
from engine.common.target_select_overlay_renderer import TargetSelectOverlay
from engine.common.warp_select_overlay import WarpSelectOverlay
from engine.common.wizard_scene import WizardPage, WizardScene
from engine.io.save_manager import GameStateManager
from engine.party.member_state import MemberState
from engine.party.party_state import exp_pct
from engine.spell.spell_logic import learned_spells, is_field_castable
from engine.status.status_logic import apply_spell, apply_spell_all, valid_targets
from engine.world.warp_logic import warp_destinations, WarpDestination
from engine.world.sprite_sheet import Direction


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
STATUS_PORTRAIT_DIR = ASSET_ROOT / "images" / "party_portraits_large"


class StatusScene(WizardScene):
    """Field party inspector. Pages: MEMBER → CATEGORY → DETAIL."""

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str = "",
        return_scene_name: str = "world_map",
        *,
        sfx_manager,
        game_state_manager: GameStateManager,
    ) -> None:
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._holder = holder
        self._scenario_path = scenario_path
        self._game_state_manager = game_state_manager

        self._spells: list[dict] = []
        self._detail_mode: str = CAT_SPELLS
        self._target_overlay: TargetSelectOverlay | None = None
        self._warp_overlay: WarpSelectOverlay | None = None
        self._popup_text: str = ""
        self._popup_active: bool = False
        self._fonts_ready = False
        # Cache of portraits already scaled to a panel size, keyed by
        # (member id, panel width, panel height) — avoids a per-frame copy
        # + smoothscale in the render loop.
        self._portrait_cache: dict[tuple[str, int, int], pygame.Surface] = {}

        self._register_page(WizardPage(
            name=PAGE_MEMBER,
            count_fn=lambda: len(self._members()),
            on_confirm=self._confirm_member,
            on_back=lambda: None,            # close scene
        ))
        self._register_page(WizardPage(
            name=PAGE_CATEGORY,
            count_fn=lambda: len(CATEGORIES),
            on_confirm=self._confirm_category,
            on_back=lambda: PAGE_MEMBER,
        ))
        self._register_page(WizardPage(
            name=PAGE_DETAIL,
            count_fn=self._detail_count,
            on_confirm=self._confirm_detail,
            on_back=lambda: PAGE_CATEGORY,
        ))

    # ── Fonts ─────────────────────────────────────────────────

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

    # ── Helpers ───────────────────────────────────────────────

    def _members(self) -> list[MemberState]:
        return list(self._holder.get().party.members)

    def _current_member(self) -> MemberState | None:
        members = self._members()
        if not members:
            return None
        sel = self._page(PAGE_MEMBER).selection
        return members[min(sel, len(members) - 1)]

    def _classes_dir(self) -> Path:
        return Path(self._scenario_path) / "data" / "classes"

    def _flags_set(self) -> set[str]:
        return set(self._holder.get().flags.to_list())

    def _load_spells(self) -> list[dict]:
        member = self._current_member()
        if member is None:
            return []
        return learned_spells(member, self._classes_dir(), self._flags_set())

    def _selected_category(self) -> str:
        return CATEGORIES[self._page(PAGE_CATEGORY).selection][0]

    def _display_name(self, item_id: str) -> str:
        catalog = self._holder.get().repository.catalog
        if catalog is not None:
            defn = catalog.get(item_id)
            if defn is not None:
                return defn.name
        return item_id.replace("_", " ").title()

    def _detail_count(self) -> int:
        if self._detail_mode == CAT_SPELLS:
            return len(self._spells)
        return len(ROWS)

    # ── Modal-overlay routing ────────────────────────────────

    def _is_input_blocked(self) -> bool:
        return (
            self._target_overlay is not None
            or self._warp_overlay is not None
            or self._popup_active
        )

    def _handle_blocked_input(self, events: list[pygame.event.Event]) -> None:
        if self._warp_overlay:
            self._warp_overlay.handle_events(events)
            return
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER,
            ):
                self._popup_active = False

    # ── Page confirm callbacks ───────────────────────────────

    def _confirm_member(self) -> str | None:
        if self._current_member() is None:
            return None
        self._play("confirm")
        return PAGE_CATEGORY

    def _confirm_category(self) -> str | None:
        cat = self._selected_category()
        if cat == CAT_SPELLS:
            self._spells = self._load_spells()
            if not self._spells:
                member = self._current_member()
                self._popup_text = f"{member.name} knows no spells."
                self._popup_active = True
                self._play("cancel")
                return None
            self._detail_mode = CAT_SPELLS
        else:
            self._detail_mode = CAT_POSITION
        self._play("confirm")
        return PAGE_DETAIL

    def _confirm_detail(self) -> str | None:
        if self._detail_mode == CAT_POSITION:
            return self._confirm_position()
        return self._confirm_spell()

    def _confirm_position(self) -> str | None:
        member = self._current_member()
        if member is None:
            return None
        new_row = ROWS[self._page(PAGE_DETAIL).selection][0]
        if member.row == new_row:
            self._play("cancel")
            return None
        member.row = new_row
        self._play("confirm")
        return None

    def _confirm_spell(self) -> str | None:
        member = self._current_member()
        if member is None or not self._spells:
            return None
        spell = self._spells[self._page(PAGE_DETAIL).selection]
        if not is_field_castable(spell):
            self._play("cancel")
            return None
        if member.mp < spell["mp_cost"]:
            self._popup_text = f"{member.name} has not enough MP."
            self._popup_active = True
            self._play("cancel")
            return None
        if spell.get("warp"):
            return self._open_warp(spell, member)
        target_type = spell.get("target")
        if target_type in ("all_allies", "party"):
            self._play("confirm")
            msg = apply_spell_all(spell, member, self._holder.get().party.members)
            self._popup_text = msg
            self._popup_active = True
            return None
        targets = valid_targets(spell, self._holder.get().party.members)
        if not targets:
            self._popup_text = "No valid targets."
            self._popup_active = True
            self._play("cancel")
            return None
        self._play("confirm")
        pending = spell
        self._target_overlay = TargetSelectOverlay(
            targets=targets,
            item_label=spell["name"],
            on_confirm=lambda t, s=pending, c=member: self._on_target_confirm(s, c, t),
            on_cancel=self._on_target_cancel,
            sfx_manager=self._sfx_manager,
        )
        return None

    # ── Teleport / target callbacks ──────────────────────────

    def _open_warp(self, spell: dict, caster: MemberState) -> str | None:
        state = self._holder.get()
        destinations = warp_destinations(state.map, Path(self._scenario_path))
        if not destinations:
            self._popup_text = "Nowhere to teleport to yet."
            self._popup_active = True
            self._play("cancel")
            return None
        self._play("confirm")
        self._warp_overlay = WarpSelectOverlay(
            destinations=destinations,
            on_confirm=lambda dest, s=spell, c=caster: self._on_warp_confirm(s, c, dest),
            on_cancel=self._on_warp_cancel,
            sfx_manager=self._sfx_manager,
        )
        return None

    def _on_warp_confirm(self, spell: dict, caster: MemberState, dest: WarpDestination) -> None:
        caster.mp = max(0, caster.mp - spell["mp_cost"])
        state = self._holder.get()
        state.map.move_to(dest.map_id, dest.position, Direction.DOWN)
        self._game_state_manager.save(state, slot_index=0)
        self._warp_overlay = None
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    def _on_warp_cancel(self) -> None:
        self._warp_overlay = None

    def _on_target_confirm(self, spell: dict, caster: MemberState, target: MemberState) -> None:
        msg = apply_spell(spell, caster, target)
        self._target_overlay = None
        self._popup_text = msg
        self._popup_active = True

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        render_backdrop(screen)
        render_header(screen, self._font_title, self._font_hint,
                      "STATUS", "party roster and growth", PAD_X, PAD_Y)

        member_rect, detail_rect, action_rect = self._layout(screen)
        render_panel(screen, member_rect, active=self.page_id == PAGE_MEMBER,
                     title="Party", title_font=self._font_head)
        self._render_members(screen, member_rect)

        member = self._current_member()
        if self.page_id == PAGE_MEMBER and member is not None:
            render_panel(screen, detail_rect)
            self._render_portrait_panel(screen, detail_rect, member)
            render_panel(screen, action_rect, title="Persona", title_font=self._font_head)
            self._render_lore_panel(screen, action_rect, member)
        elif self.page_id in (PAGE_CATEGORY, PAGE_DETAIL) and member is not None:
            render_panel(screen, detail_rect, active=self.page_id == PAGE_CATEGORY,
                         title=member.name, title_font=self._font_head)
            self._render_detail_panel(screen, detail_rect, member)
            if self.page_id == PAGE_CATEGORY:
                render_panel(screen, action_rect, title="Persona", title_font=self._font_head)
                self._render_lore_panel(screen, action_rect, member)
        if self.page_id == PAGE_DETAIL and member is not None:
            title = "Spells" if self._detail_mode == CAT_SPELLS else "Position"
            render_panel(screen, action_rect, active=True,
                         title=title, title_font=self._font_head)
            if self._detail_mode == CAT_SPELLS:
                self._render_spells(screen, action_rect, member)
            else:
                self._render_position(screen, action_rect, member)

        self._render_hint(screen)

        if self._target_overlay:
            self._target_overlay.render(screen)
        if self._warp_overlay:
            self._warp_overlay.render(screen)
        if self._popup_active:
            render_popup(screen, self._font_row, self._font_meta, self._popup_text)

    def _layout(self, screen: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        sw, sh = screen.get_size()
        top = PAD_Y + 92
        panel_h = max(360, sh - top - 62)
        available = sw - PAD_X * 2 - GAP * 2
        member_w = min(300, max(260, int(sw * 0.24)))
        remaining = available - member_w
        detail_w = remaining // 2
        action_w = remaining - detail_w
        member_rect = pygame.Rect(PAD_X, top, member_w, panel_h)
        detail_rect = pygame.Rect(member_rect.right + GAP, top, detail_w, panel_h)
        action_rect = pygame.Rect(detail_rect.right + GAP, top, action_w, panel_h)
        return member_rect, detail_rect, action_rect

    # ── Col 1: party cards (matches the equipment party panel) ─

    def _render_members(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        members = self._members()
        x = panel.x + 16
        top = panel.y + 52
        w = panel.w - 32
        if not members:
            msg = self._font_row.render("No members.", True, C_TEXT_DIM)
            screen.blit(msg, (x, top))
            return
        sel = self._page(PAGE_MEMBER).selection
        active_page = self.page_id == PAGE_MEMBER

        n = len(members)
        gap = 14
        avail = (panel.bottom - 16) - top
        row_h = min(118, (avail - gap * (n - 1)) // n)
        portrait = min(row_h - 16, 92)

        for i, m in enumerate(members):
            selected = (i == sel)
            row = pygame.Rect(x, top + i * (row_h + gap), w, row_h)
            self._render_member_card(
                screen, row, m, portrait,
                focused=selected and active_page,
                dimmed=selected and not active_page,
            )

    def _render_member_card(
        self, screen: pygame.Surface, rect: pygame.Rect, m: MemberState,
        portrait: int, *, focused: bool, dimmed: bool,
    ) -> None:
        render_row_frame(screen, rect, focused=focused, dimmed_sel=dimmed)
        icon = icon_surface(f"member_{m.id}", portrait, image_path=member_icon_path(m.id))
        screen.blit(icon, (rect.x + 12, rect.y + (rect.h - portrait) // 2))

        tx = rect.x + 24 + portrait
        max_w = rect.right - tx - 14
        name = fit_text(self._font_head, f"{m.name}  Lv{m.level}", INK, max_w)
        cls = fit_text(self._font_row, m.class_name.title(), GOLD, max_w)
        hp = self._font_meta.render(f"HP {m.hp}/{m.hp_max}", True, MUTED)
        mp = self._font_meta.render(f"MP {m.mp}/{m.mp_max}", True, MUTED)

        line_gap = 6
        block_h = (name.get_height() + line_gap + cls.get_height()
                   + line_gap + max(hp.get_height(), mp.get_height()))
        ty = rect.y + (rect.h - block_h) // 2
        screen.blit(name, (tx, ty))
        ty += name.get_height() + line_gap
        screen.blit(cls, (tx, ty))
        ty += cls.get_height() + line_gap
        screen.blit(hp, (tx, ty))
        screen.blit(mp, (tx + max(hp.get_width() + 18, 96), ty))

    # ── Col 2: member detail + action menu ────────────────────

    def _render_portrait_panel(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        cache_key = (m.id, panel.w, panel.h)
        portrait = self._portrait_cache.get(cache_key)
        if portrait is None:
            image_path = _status_portrait_path(m.id)
            image = load_image(image_path) if image_path is not None else None
            if image is None:
                msg = self._font_row.render("No portrait.", True, C_TEXT_DIM)
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
        screen.blit(self._font_meta.render(meta, True, MUTED), (x, y))
        y += self._font_meta.get_height() + 18

        y = self._render_lore_section(screen, x, y, w, "Persona", lore.get("persona", ""))
        y += 12
        y = self._render_lore_section(screen, x, y, w, "Backstory", lore.get("backstory", ""))
        argument = lore.get("argument", "")
        if argument and y < panel.bottom - 72:
            draw_divider(screen, x, y + 4, w)
            y += 18
            screen.blit(self._font_meta.render("Throughline", True, GOLD), (x, y))
            y += self._font_meta.get_height() + 5
            for line in wrap_text(self._font_small, argument, w, limit=3):
                screen.blit(self._font_small.render(line, True, MUTED), (x, y))
                y += self._font_small.get_height() + 3

    def _render_lore_section(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        w: int,
        label: str,
        text: str,
    ) -> int:
        screen.blit(self._font_meta.render(label, True, GOLD), (x, y))
        y += self._font_meta.get_height() + 5
        if not text:
            text = "No record."
        for line in wrap_text(self._font_small, text, w, limit=7):
            screen.blit(self._font_small.render(line, True, INK), (x, y))
            y += self._font_small.get_height() + 3
        return y

    def _render_detail_panel(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        x = panel.x + 18
        w = panel.w - 36
        y = panel.y + 52

        # Level + EXP
        screen.blit(self._font_stat.render(f"Lv {m.level}", True, INK), (x, y))
        exp_txt = self._font_meta.render(f"EXP {m.exp}/{m.exp_next}", True, MUTED)
        screen.blit(exp_txt, (panel.right - 18 - exp_txt.get_width(), y + 2))
        y += self._font_stat.get_height() + 6
        self._bar(screen, x, y, w, exp_pct(m), VIOLET)
        y += BAR_H + 14

        # HP / MP bars
        hp_pct = m.hp / m.hp_max if m.hp_max > 0 else 0
        hp_col = HP_BAR_LOW if hp_pct < HP_LOW_THRESHOLD else HP_BAR_OK
        y = self._stat_bar_row(screen, x, y, w, "HP", f"{m.hp}/{m.hp_max}", hp_pct, hp_col)
        if m.mp_max > 0:
            y = self._stat_bar_row(screen, x, y, w, "MP", f"{m.mp}/{m.mp_max}", m.mp / m.mp_max, TEAL)
        else:
            screen.blit(self._font_meta.render("MP  -", True, DIM), (x, y))
            y += self._font_meta.get_height() + BAR_H + 6
        y += 6

        # Stats grid (2 columns)
        col2_x = x + w // 2
        line_h = self._font_stat.get_height() + 8
        stat_vals = {"str": m.str_, "dex": m.dex, "con": m.con, "int": m.int_}
        for i, (key, label) in enumerate(STAT_ORDER):
            cx = x if i % 2 == 0 else col2_x
            cy = y + (i // 2) * line_h
            screen.blit(self._font_meta.render(label, True, MUTED), (cx, cy))
            screen.blit(self._font_stat.render(str(stat_vals[key]), True, INK), (cx + 42, cy - 1))
        y += 2 * line_h + 6

        # Gear
        for slot, label in GEAR_ORDER:
            item_id = m.equipped.get(slot)
            val = self._display_name(item_id) if item_id else "-"
            screen.blit(self._font_meta.render(label, True, MUTED), (x, y))
            screen.blit(fit_text(self._font_meta, val,
                                 INK if item_id else DIM, w - 48), (x + 48, y))
            y += self._font_meta.get_height() + 4

        # Action menu, anchored to the bottom of the panel
        self._render_category_menu(screen, panel, m)

    def _render_category_menu(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        x = panel.x + 16
        w = panel.w - 32
        menu_h = len(CATEGORIES) * (ROW_H + 8)
        y = panel.bottom - 18 - menu_h
        draw_divider(screen, x, y - 12, w)

        sel = self._page(PAGE_CATEGORY).selection
        on_category = self.page_id == PAGE_CATEGORY
        for i, (key, label) in enumerate(CATEGORIES):
            selected = (i == sel)
            right = m.row.title() if key == CAT_POSITION else ""
            rect = pygame.Rect(x, y + i * (ROW_H + 8), w, ROW_H)
            render_icon_row(
                screen, self._font_row, rect, label,
                icon_key=f"cat_{key}",
                focused=selected and on_category,
                dimmed_sel=selected and self.page_id == PAGE_DETAIL,
                color=INK,
                right_text=right,
                right_font=self._font_meta,
            )

    # ── Col 3: spells or position ─────────────────────────────

    def _render_spells(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        x = panel.x + 16
        y = panel.y + 52
        w = panel.w - 32
        if not self._spells:
            screen.blit(self._font_row.render("No spells learned.", True, DIM), (x, y))
            return
        sel = self._page(PAGE_DETAIL).selection
        for i, spell in enumerate(self._spells):
            selected = (i == sel)
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
                screen, self._font_row, rect, spell["name"],
                icon_key=_spell_icon_key(spell),
                focused=selected,
                dimmed_sel=False,
                color=color,
                right_text=f"MP {spell['mp_cost']}",
                right_font=self._font_meta,
                subtext=f"{badge} / {spell.get('target', 'self')}",
                sub_font=self._font_small,
            )

        spell = self._spells[sel]
        desc = spell.get("description", "")
        if desc:
            dy = panel.bottom - 70
            draw_divider(screen, x, dy - 10, w)
            for line in wrap_text(self._font_meta, desc, w, limit=3):
                screen.blit(self._font_meta.render(line, True, MUTED), (x, dy))
                dy += self._font_meta.get_height() + 3

    def _render_position(self, screen: pygame.Surface, panel: pygame.Rect, m: MemberState) -> None:
        x = panel.x + 16
        y = panel.y + 52
        w = panel.w - 32
        sel = self._page(PAGE_DETAIL).selection
        for i, (key, label) in enumerate(ROWS):
            selected = (i == sel)
            current = (m.row == key)
            rect = pygame.Rect(x, y + i * (ROW_H + 8), w, ROW_H)
            render_icon_row(
                screen, self._font_row, rect, label,
                icon_key=f"row_{key}",
                focused=selected,
                dimmed_sel=False,
                color=INK,
                right_text="current" if current else "",
                right_font=self._font_meta,
            )

    # ── Shared bar helpers ────────────────────────────────────

    def _bar(self, screen, x, y, w, pct, color) -> None:
        pygame.draw.rect(screen, BAR_TRACK, (x, y, w, BAR_H), border_radius=3)
        pygame.draw.rect(screen, color, (x, y, int(w * max(0.0, min(1.0, pct))), BAR_H), border_radius=3)

    def _stat_bar_row(self, screen, x, y, w, label, value, pct, color) -> int:
        lbl = self._font_meta.render(label, True, color)
        val = self._font_meta.render(value, True, MUTED)
        screen.blit(lbl, (x, y))
        screen.blit(val, (x + w - val.get_width(), y))
        bar_y = y + lbl.get_height() + 2
        self._bar(screen, x, bar_y, w, pct, color)
        return bar_y + BAR_H + 8

    # ── Hint ──────────────────────────────────────────────────

    def _render_hint(self, screen: pygame.Surface) -> None:
        sw, sh = screen.get_size()
        if self.page_id == PAGE_MEMBER:
            text = "UP/DOWN select member    ENTER stats    ESC close"
        elif self.page_id == PAGE_CATEGORY:
            text = "UP/DOWN select    ENTER open    ESC back"
        elif self._detail_mode == CAT_SPELLS:
            text = "UP/DOWN select spell    ENTER cast    ESC back"
        else:
            text = "UP/DOWN select row    ENTER set    ESC back"
        hint = self._font_hint.render(text, True, C_TEXT_DIM)
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - 30))


def _spell_icon_key(spell: dict) -> str:
    if spell.get("warp"):
        return "spell_warp"
    element = spell.get("element")
    if element:
        return f"spell_{element}"
    return f"spell_{spell.get('type', 'utility')}"


def _status_portrait_path(member_id: str) -> Path | None:
    path = STATUS_PORTRAIT_DIR / f"{member_id}_status_portrait.webp"
    if path.exists():
        return path
    return member_icon_path(member_id)
