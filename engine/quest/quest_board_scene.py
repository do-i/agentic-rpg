# engine/quest/quest_board_scene.py
#
# Quest Board — full-screen scene opened from the field menu. Lists every
# quest in the scenario registry (data/quests.yaml) with a MAIN/SUB tag and
# a flag-derived status: Not Started / In Progress / Completed. Read-only;
# quest progress itself is driven entirely by dialogue flags.

from __future__ import annotations

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.font_provider import get_fonts
from engine.common.font_roles import CAPTION
from engine.common.menu_sfx_mixin import MenuSfxMixin
from engine.common.scroll_list import ScrollListState
from engine.common.ui.theme import DIM, GOLD, INK, MUTED, TEAL
from engine.common.ui.chrome import (
    render_backdrop,
    render_header,
    render_panel,
    render_row_frame,
    wrap_text,
)
from engine.quest.quest_catalog import (
    QuestCatalog,
    QuestDef,
    QUEST_TYPE_MAIN,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
)

VISIBLE_ROWS = 7
ROW_H = 52
ROW_GAP = 6
LIST_TOP = 122
DETAIL_H = 132
HINT_MARGIN_Y = 32
BOARD_SUBTITLE = "the road so far"

_STATUS_LABEL = {
    STATUS_NOT_STARTED: "Not Started",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_COMPLETED:   "Completed",
}
_STATUS_COLOR = {
    STATUS_NOT_STARTED: DIM,
    STATUS_IN_PROGRESS: GOLD,
    STATUS_COMPLETED:   TEAL,
}


class QuestBoardScene(MenuSfxMixin, Scene):
    """Scrollable quest list + detail panel for the selected quest."""

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        quest_catalog: QuestCatalog,
        return_scene_name: str,
        sfx_manager,
    ) -> None:
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._catalog = quest_catalog
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager
        self._list = ScrollListState(VISIBLE_ROWS)
        self._fonts_ready = False

    def set_return_scene(self, name: str) -> None:
        """Field menu calls this so ESC returns there instead of world map."""
        self._return_scene_name = name

    # ── Fonts ─────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(32, bold=True)
        self._font_entry = f.get(20, bold=True)
        self._font_meta  = f.get(CAPTION)
        self._font_tag   = f.get(14, bold=True)
        self._font_hint  = f.get(15)
        self._font_panel = f.get(18, bold=True)
        self._fonts_ready = True

    # ── Data ──────────────────────────────────────────────────

    def _quests(self) -> tuple[QuestDef, ...]:
        return self._catalog.quests

    def _status(self, quest: QuestDef) -> str:
        return QuestCatalog.status(quest, self._holder.get().flags)

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                if self._list.move(-1, len(self._quests())):
                    self._play("hover")
            elif event.key == pygame.K_DOWN:
                if self._list.move(1, len(self._quests())):
                    self._play("hover")
            elif event.key in (pygame.K_ESCAPE, pygame.K_m, pygame.K_q):
                self._close()

    def _close(self) -> None:
        self._play("cancel")
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        sw, sh = screen.get_size()
        render_backdrop(screen)
        render_header(
            screen, self._font_title, self._font_hint,
            "QUEST BOARD", BOARD_SUBTITLE, 52, 34,
        )

        quests = self._quests()
        list_w = min(760, max(560, int(sw * 0.62)))
        list_h = 54 + VISIBLE_ROWS * (ROW_H + ROW_GAP) + 12
        list_rect = pygame.Rect((sw - list_w) // 2, LIST_TOP, list_w, list_h)
        title = f"Quests  {self._list.selection + 1}/{len(quests)}" if quests else "Quests"
        render_panel(screen, list_rect, active=True, title=title, title_font=self._font_panel)
        self._render_rows(screen, list_rect, quests)

        detail_rect = pygame.Rect(
            list_rect.x, list_rect.bottom + 10, list_w, DETAIL_H,
        )
        render_panel(screen, detail_rect, active=False, title="Details", title_font=self._font_panel)
        selected = self._list.selected(quests)
        if selected is not None:
            self._render_detail(screen, detail_rect, selected)

        hint = self._font_hint.render(
            "UP/DOWN select    ESC back", True, DIM,
        )
        screen.blit(hint, ((sw - hint.get_width()) // 2, sh - HINT_MARGIN_Y))

    def _render_rows(
        self,
        screen: pygame.Surface,
        panel: pygame.Rect,
        quests: tuple[QuestDef, ...],
    ) -> None:
        x = panel.x + 18
        y = panel.y + 48
        w = panel.w - 36
        window = quests[self._list.scroll:self._list.scroll + VISIBLE_ROWS]
        for i, quest in enumerate(window):
            index = self._list.scroll + i
            focused = (index == self._list.selection)
            rect = pygame.Rect(x, y + i * (ROW_H + ROW_GAP), w, ROW_H)
            render_row_frame(screen, rect, focused=focused)

            status = self._status(quest)
            tag_is_main = (quest.type == QUEST_TYPE_MAIN)
            tag = self._font_tag.render(
                "MAIN" if tag_is_main else "SUB",
                True, GOLD if tag_is_main else MUTED,
            )
            screen.blit(tag, (rect.x + 14, rect.y + (rect.h - tag.get_height()) // 2))

            name_color = INK if status != STATUS_NOT_STARTED or focused else MUTED
            name = self._font_entry.render(quest.name, True, name_color)
            screen.blit(name, (rect.x + 70, rect.y + 7))
            location = self._font_meta.render(quest.location, True, DIM)
            screen.blit(location, (rect.x + 70, rect.y + 9 + name.get_height()))

            label = self._font_entry.render(
                _STATUS_LABEL[status], True, _STATUS_COLOR[status],
            )
            screen.blit(label, (
                rect.right - label.get_width() - 16,
                rect.y + (rect.h - label.get_height()) // 2,
            ))

    def _render_detail(
        self,
        screen: pygame.Surface,
        panel: pygame.Rect,
        quest: QuestDef,
    ) -> None:
        x = panel.x + 18
        y = panel.y + 44
        w = panel.w - 36
        line_h = self._font_meta.get_height() + 4
        for i, line in enumerate(wrap_text(self._font_meta, quest.description, w)):
            if y + i * line_h > panel.bottom - line_h - 8:
                break
            surf = self._font_meta.render(line, True, MUTED)
            screen.blit(surf, (x, y + i * line_h))
