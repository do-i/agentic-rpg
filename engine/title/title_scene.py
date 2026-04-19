# engine/scenes/title_scene.py

import pygame
from engine.audio.bgm_manager import BgmManager
from engine.common.font_provider import get_fonts
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
        bgm_manager: BgmManager | None = None,
    ) -> None:
        self._manifest = loader.load()
        self._scenario_path = loader.scenario_path
        self._scene_manager = scene_manager
        self._registry = registry
        self._game_state_manager = game_state_manager
        self._sfx_manager = sfx_manager
        self._bgm_manager = bgm_manager
        self._menu_font = None
        self._menu = None
        self._has_saves: bool = False
        self._bg_image: pygame.Surface | None = None

    def _init_fonts(self) -> None:
        self._menu_font = get_fonts().get(30)

        title_cfg = self._manifest.get("title", {})
        image_ref = title_cfg.get("image")
        if image_ref:
            bg_path = self._scenario_path / image_ref
            if bg_path.exists():
                self._bg_image = pygame.image.load(str(bg_path)).convert_alpha()

        cursor_icon = None
        cursor_ref = title_cfg.get("cursor_icon")
        if cursor_ref:
            cursor_path = self._scenario_path / cursor_ref
            if cursor_path.exists():
                raw = pygame.image.load(str(cursor_path)).convert_alpha()
                w = max(1, int(raw.get_width() * 0.3))
                h = max(1, int(raw.get_height() * 0.3))
                cursor_icon = pygame.transform.smoothscale(raw, (w, h))

        # check if any non-empty save slots exist
        slots = self._game_state_manager.list_slots()
        self._has_saves = any(not s.is_empty for s in slots)

        self._menu = Menu(
            items=["New Game", "Load Game", "Quit"],
            font=self._menu_font,
            color_normal=(170, 140, 100),
            color_selected=(220, 140, 60),
            color_disabled=(80, 70, 55),
            line_height=42,
            sfx_manager=self._sfx_manager,
            cursor_icon=cursor_icon,
        )

        if self._bgm_manager:
            self._bgm_manager.play_key("title.default")

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

        if self._bg_image is not None:
            bx = (screen.get_width()  - self._bg_image.get_width())  // 2
            by = (screen.get_height() - self._bg_image.get_height()) // 2
            screen.blit(self._bg_image, (bx, by))

        # gray out Load Game if no saves
        if not self._has_saves:
            self._menu.set_item_disabled("Load Game", True)

        # Menu fills bottom 30% of the screen, centered, with a 50%-opacity box.
        menu_area_top = int(screen.get_height() * 0.70)
        menu_area_h = screen.get_height() - menu_area_top
        line_h = 42
        cursor_w = self._menu.cursor_width
        pad_x, pad_y = 30, 20
        max_text_w = max(
            self._menu_font.size(item)[0] for item in ["New Game", "Load Game", "Quit"]
        )
        box_w = max_text_w + cursor_w + pad_x * 2
        box_h = 3 * line_h + pad_y * 2
        box_x = (screen.get_width() - box_w) // 2
        box_y = menu_area_top + (menu_area_h - box_h) // 2

        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(
            box_surf,
            (0, 0, 0, 28),
            box_surf.get_rect(),
            border_radius=12,
        )
        screen.blit(box_surf, (box_x, box_y))

        self._menu.render(screen, box_x + pad_x, box_y + pad_y)
