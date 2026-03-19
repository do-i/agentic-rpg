# engine/core/scenes/world_map_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.state.game_state_holder import GameStateHolder
from engine.data.loader import ManifestLoader
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory


class WorldMapScene(Scene):
    """
    Phase 1 — tile map rendering only.
    Player movement and camera added in next step.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        loader: ManifestLoader,
        tile_map_factory: TileMapFactory,
        scene_manager: SceneManager,
        registry: SceneRegistry,
    ) -> None:
        self._holder = holder
        self._loader = loader
        self._tile_map_factory = tile_map_factory
        self._scene_manager = scene_manager
        self._registry = registry
        self._tile_map: TileMap | None = None

    def _init(self) -> None:
        """Lazy init — deferred until first render."""
        scenario_path = self._loader.scenario_path
        map_id = self._holder.get().map.current
        tmx_path = scenario_path / "data" / "tmx" / f"{map_id}.tmx"
        self._tile_map = self._tile_map_factory.create(str(tmx_path))

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass  # controls added in next step

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass  # movement added in next step

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._tile_map is None:
            self._init()

        screen.fill((0, 0, 0))
        self._tile_map.render(screen, 0, 0)
