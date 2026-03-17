# engine/core/scenes/title_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.data.loader import ManifestLoader
from engine.ui.menu import Menu


class TitleScene(Scene):
    def __init__(
        self,
        loader: ManifestLoader,
        scene_manager: SceneManager,
        registry: SceneRegistry,
    ) -> None:
        self._manifest = loader.load()
        self._scene_manager = scene_manager
        self._registry = registry
        self._title = self._manifest.get("name", "RPG")
        self._title_font = None
        self._menu_font = None
        self._menu = None

    def _init_fonts(self) -> None:
        self._title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self._menu_font = pygame.font.SysFont("Arial", 36)
        self._menu = Menu(
            items=["New Game", "Load Game", "Quit"],
            font=self._menu_font,
        )

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._menu is None:
            return
        confirmed = self._menu.handle_events(events)
        if confirmed:
            self._on_select()

    def _on_select(self) -> None:
        item = self._menu.selected_item
        if item == "Quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif item == "New Game":
            self._scene_manager.switch(self._registry.get("name_entry"))
        elif item == "Load Game":
            pass  # LoadGameScene plugs in here

    def render(self, screen: pygame.Surface) -> None:
        if self._menu is None:
            self._init_fonts()

        screen.fill((10, 10, 30))

        text = self._title_font.render(self._title, True, (220, 220, 180))
        x = (Settings.SCREEN_WIDTH - text.get_width()) // 2
        screen.blit(text, (x, 180))

        menu_x = (Settings.SCREEN_WIDTH - 200) // 2
        self._menu.render(screen, menu_x, 380)
