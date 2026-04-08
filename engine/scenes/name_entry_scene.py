# engine/scenes/name_entry_scene.py

import pygame
from engine.scenes.scene import Scene
from engine.scenes.scene_manager import SceneManager
from engine.scenes.scene_registry import SceneRegistry
from engine.settings import Settings
from engine.io.item_catalog import ItemCatalog
from engine.dto.game_state_holder import GameStateHolder
from engine.io.game_state_loader import from_new_game
from engine.io.manifest_loader import ManifestLoader
from engine.debug.debug_bootstrap import inject_full_party


NAME_MAX_LENGTH = 12


class NameEntryScene(Scene):
    """
    Prompts the player to enter the protagonist's name.
    On confirm → bootstraps GameState → sets holder → switches to world_map.
    """

    def __init__(
        self,
        loader: ManifestLoader,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        holder: GameStateHolder,
        item_catalog: ItemCatalog | None = None,
        debug_party: bool = False,
    ) -> None:
        self._manifest     = loader.load()
        self._scenario_path = loader.scenario_path
        self._classes_dir  = loader.scenario_path / "data" / "classes"
        self._scene_manager = scene_manager
        self._registry     = registry
        self._holder       = holder
        self._item_catalog = item_catalog
        self._debug_party  = debug_party
        self._name: str    = self._manifest["protagonist"]["name"]
        self._prompt_font  = None
        self._input_font   = None
        self._hint_font    = None

    def _init_fonts(self) -> None:
        self._prompt_font = pygame.font.SysFont("Arial", 36)
        self._input_font  = pygame.font.SysFont("Arial", 48, bold=True)
        self._hint_font   = pygame.font.SysFont("Arial", 24)

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.TEXTINPUT:
                if len(self._name) < NAME_MAX_LENGTH:
                    self._name += event.text
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self._name = self._name[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm()

    def _confirm(self) -> None:
        name  = self._name.strip() or self._manifest["protagonist"]["name"]
        state = from_new_game(
            self._manifest, name, self._classes_dir, self._scenario_path,
            item_catalog=self._item_catalog,
        )

        if self._debug_party:
            inject_full_party(state, self._scenario_path)

        self._holder.set(state)
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._prompt_font is None:
            self._init_fonts()
            pygame.key.start_text_input()

        screen.fill((10, 10, 30))
        cx = Settings.SCREEN_WIDTH  // 2
        cy = Settings.SCREEN_HEIGHT // 2

        prompt = self._prompt_font.render("Enter your name", True, (180, 180, 140))
        screen.blit(prompt, (cx - prompt.get_width() // 2, cy - 100))

        box_w, box_h = 320, 60
        box_x = cx - box_w // 2
        box_y = cy - box_h // 2
        pygame.draw.rect(screen, (40, 40, 70),   (box_x, box_y, box_w, box_h))
        pygame.draw.rect(screen, (180, 180, 100), (box_x, box_y, box_w, box_h), 2)

        display   = self._name + "|"
        name_surf = self._input_font.render(display, True, (255, 220, 80))
        screen.blit(name_surf, (cx - name_surf.get_width() // 2, box_y + 8))

        count = self._hint_font.render(
            f"{len(self._name)}/{NAME_MAX_LENGTH}", True, (120, 120, 100)
        )
        screen.blit(count, (box_x + box_w - count.get_width() - 8, box_y + box_h + 8))

        hint = self._hint_font.render("ENTER to confirm", True, (120, 120, 100))
        screen.blit(hint, (cx - hint.get_width() // 2, cy + 80))

        if self._debug_party:
            dbg = self._hint_font.render("[DEBUG] full party enabled", True, (180, 100, 100))
            screen.blit(dbg, (cx - dbg.get_width() // 2, cy + 120))
