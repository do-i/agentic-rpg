# engine/core/scenes/game_over_scene.py
#
# Game Over screen — shown on party wipe.

from __future__ import annotations

import pygame

from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.game_state_manager import GameStateManager

# ── Colors ────────────────────────────────────────────────────
C_BG         = (8, 4, 12)
C_TITLE      = (180, 50, 50)
C_TEXT        = (200, 200, 200)
C_SELECTED   = (255, 220, 80)
C_DISABLED   = (80, 80, 80)
C_HINT       = (100, 100, 115)

MENU_ITEMS   = ["Load Game", "Title Screen", "Quit"]


class GameOverScene(Scene):
    """
    Game Over screen with load/title/quit options.
    """

    def __init__(
        self,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        holder: GameStateHolder,
        game_state_manager: GameStateManager,
    ) -> None:
        self._scene_manager = scene_manager
        self._registry = registry
        self._holder = holder
        self._game_state_manager = game_state_manager
        self._sel = 0
        self._fonts_ready = False
        self._has_saves = False
        self._fade_alpha = 0
        self._fade_done = False

    def _init_fonts(self) -> None:
        self._font_title = pygame.font.SysFont("Arial", 56, bold=True)
        self._font_menu  = pygame.font.SysFont("Arial", 28)
        self._font_hint  = pygame.font.SysFont("Arial", 16)
        self._fonts_ready = True

        slots = self._game_state_manager.list_slots()
        self._has_saves = any(not s.is_empty for s in slots)
        if not self._has_saves:
            # skip Load Game, start on Title Screen
            self._sel = 1

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if not self._fade_done:
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_UP:
                self._sel = max(0, self._sel - 1)
                if not self._has_saves and self._sel == 0:
                    self._sel = 1
            elif event.key == pygame.K_DOWN:
                self._sel = min(len(MENU_ITEMS) - 1, self._sel + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm()

    def _confirm(self) -> None:
        item = MENU_ITEMS[self._sel]
        if item == "Load Game" and self._has_saves:
            self._scene_manager.switch(self._registry.get("load_game"))
        elif item == "Title Screen":
            self._scene_manager.switch(self._registry.get("title"))
        elif item == "Quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if not self._fade_done:
            self._fade_alpha = min(255, self._fade_alpha + int(200 * delta))
            if self._fade_alpha >= 255:
                self._fade_done = True

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(C_BG)

        cx = Settings.SCREEN_WIDTH // 2
        cy = Settings.SCREEN_HEIGHT // 2

        # title
        title = self._font_title.render("Game Over", True, C_TITLE)
        title_y = cy - 100
        screen.blit(title, (cx - title.get_width() // 2, title_y))

        # menu
        menu_y = cy + 10
        for i, label in enumerate(MENU_ITEMS):
            selected = i == self._sel
            disabled = label == "Load Game" and not self._has_saves

            if disabled:
                color = C_DISABLED
            elif selected:
                color = C_SELECTED
            else:
                color = C_TEXT

            text = self._font_menu.render(label, True, color)
            x = cx - text.get_width() // 2
            y = menu_y + i * 44

            if selected and not disabled:
                cursor = self._font_menu.render("▶  ", True, C_SELECTED)
                screen.blit(cursor, (x - cursor.get_width(), y))

            screen.blit(text, (x, y))

        # fade-in overlay
        if not self._fade_done:
            overlay = pygame.Surface(
                (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 255 - self._fade_alpha))
            screen.blit(overlay, (0, 0))
