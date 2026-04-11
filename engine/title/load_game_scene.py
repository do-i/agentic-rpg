# engine/scenes/load_game_scene.py

import pygame
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.settings import Settings
from engine.common.io.save_manager import GameStateManager
from engine.common.game_state_holder import GameStateHolder
from engine.common.save_slot_data import SaveSlot

SLOT_HEIGHT = 44
VISIBLE_SLOTS = 10
MODAL_W = 760
MODAL_H = 540


class LoadGameScene(Scene):
    """
    Full-screen load scene accessible from Title Screen.
    Lists all save slots; selecting a non-empty slot loads it.
    """

    def __init__(
        self,
        game_state_manager: GameStateManager,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        sfx_manager=None,
    ) -> None:
        self._game_state_manager = game_state_manager
        self._holder = holder
        self._scene_manager = scene_manager
        self._registry = registry
        self._sfx_manager = sfx_manager
        self._slots: list[SaveSlot] = []
        self._selected = 0
        self._scroll_offset = 0
        self._fonts_ready = False

    def _init(self) -> None:
        self._font_title = pygame.font.SysFont("Arial", 32, bold=True)
        self._font_slot  = pygame.font.SysFont("Arial", 22)
        self._font_hint  = pygame.font.SysFont("Arial", 18)
        self._fonts_ready = True
        self._slots = self._game_state_manager.list_slots()
        # start selection at first non-empty slot
        for i, s in enumerate(self._slots):
            if not s.is_empty:
                self._selected = i
                break

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._scene_manager.switch(self._registry.get("title"))
            elif event.key == pygame.K_UP:
                self._move(-1)
            elif event.key == pygame.K_DOWN:
                self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._load_selected()

    def _move(self, delta: int) -> None:
        total = len(self._slots)
        old = self._selected
        self._selected = max(0, min(self._selected + delta, total - 1))
        if self._selected != old and self._sfx_manager:
            self._sfx_manager.play("hover")
        self._clamp_scroll()

    def _clamp_scroll(self) -> None:
        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + VISIBLE_SLOTS:
            self._scroll_offset = self._selected - VISIBLE_SLOTS + 1

    def _load_selected(self) -> None:
        slot = self._slots[self._selected]
        if slot.is_empty or slot.path is None:
            return
        if self._sfx_manager:
            self._sfx_manager.play("confirm")
        state = self._game_state_manager.load(slot.path)
        self._holder.set(state)
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init()

        screen.fill((10, 10, 30))
        mx = (Settings.SCREEN_WIDTH - MODAL_W) // 2
        my = (Settings.SCREEN_HEIGHT - MODAL_H) // 2

        pygame.draw.rect(screen, (20, 20, 45), (mx, my, MODAL_W, MODAL_H))
        pygame.draw.rect(screen, (160, 160, 100), (mx, my, MODAL_W, MODAL_H), 2)

        title = self._font_title.render("LOAD GAME", True, (220, 220, 180))
        screen.blit(title, (mx + 20, my + 14))

        pygame.draw.line(screen, (80, 80, 60), (mx + 10, my + 55), (mx + MODAL_W - 10, my + 55))

        for i in range(VISIBLE_SLOTS):
            idx = self._scroll_offset + i
            if idx >= len(self._slots):
                break
            slot = self._slots[idx]
            row_y = my + 65 + i * SLOT_HEIGHT
            selected = (idx == self._selected)
            self._render_row(screen, slot, mx, row_y, selected)

        hint = self._font_hint.render("ENTER — Load    ESC — Back", True, (120, 120, 90))
        screen.blit(hint, (mx + 20, my + MODAL_H - 28))

    def _render_row(
        self,
        screen: pygame.Surface,
        slot: SaveSlot,
        mx: int,
        y: int,
        selected: bool,
    ) -> None:
        bg = (40, 40, 70) if selected else (25, 25, 45)
        pygame.draw.rect(screen, bg, (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4))

        if selected:
            cur = self._font_slot.render("▶", True, (255, 220, 50))
            screen.blit(cur, (mx + 14, y + 8))

        empty = slot.is_empty
        label_col = (200, 200, 160) if not empty else (90, 90, 80)
        label = self._font_slot.render(slot.label, True, label_col)
        screen.blit(label, (mx + 38, y + 8))

        detail_col = (160, 160, 120) if selected else (110, 110, 90)
        detail = self._font_slot.render(slot.display_line(), True, detail_col)
        screen.blit(detail, (mx + 150, y + 8))
