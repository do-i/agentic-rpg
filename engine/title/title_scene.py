# engine/scenes/title_scene.py

import pygame
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.io.save_manager import GameStateManager
from engine.io.manifest_loader import ManifestLoader
from engine.title.menu_renderer import Menu


class TitleScene(Scene):
    def __init__(
        self,
        loader: ManifestLoader,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        game_state_manager: GameStateManager,
        sfx_manager=None,
    ) -> None:
        self._manifest = loader.load()
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._sfx_manager = sfx_manager
        self._title = self._manifest.get("name", "RPG")
        self._title_font = None
        self._menu_font = None
        self._menu = None
        self._has_saves: bool = False

    def _init_fonts(self) -> None:
        self._title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self._menu_font  = pygame.font.SysFont("Arial", 36)

        # check if any non-empty save slots exist
        slots = self._game_state_manager.list_slots()
        self._has_saves = any(not s.is_empty for s in slots)

        self._menu = Menu(
            items=["New Game", "Load Game", "Quit"],
            font=self._menu_font,
            sfx_manager=self._sfx_manager,
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
            if self._has_saves:
                self._scene_manager.switch(self._registry.get("load_game"))

    def render(self, screen: pygame.Surface) -> None:
        if self._menu is None:
            self._init_fonts()

        screen.fill((10, 10, 30))

        text = self._title_font.render(self._title, True, (220, 220, 180))
        x = (screen.get_width() - text.get_width()) // 2
        screen.blit(text, (x, 180))

        # gray out Load Game if no saves
        if not self._has_saves:
            self._menu.set_item_disabled("Load Game", True)

        menu_x = (screen.get_width() - 200) // 2
        self._menu.render(screen, menu_x, 380)
