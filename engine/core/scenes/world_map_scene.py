# engine/core/scenes/world_map_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.state.game_state_holder import GameStateHolder
from engine.data.loader import ManifestLoader
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory
from engine.world.camera import Camera
from engine.world.player import Player


class WorldMapScene(Scene):
    """
    Phase 1 — tile map rendering + player movement + camera.
    NPC, encounters, transitions stubbed for later phases.
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
        self._camera: Camera | None = None
        self._player: Player | None = None

    def _init(self) -> None:
        """Lazy init — deferred until first render."""
        scenario_path = self._loader.scenario_path
        map_id = self._holder.get().map.current
        tmx_path = scenario_path / "data" / "tmx" / f"{map_id}.tmx"

        self._tile_map = self._tile_map_factory.create(str(tmx_path))
        self._camera = Camera(self._tile_map.width_px, self._tile_map.height_px)
        self._player = Player(
            start=self._holder.get().map.position,
            map_width_px=self._tile_map.width_px,
            map_height_px=self._tile_map.height_px,
        )

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pass  # pause menu — Phase 2

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._player is None:
            return
        keys = pygame.key.get_pressed()
        self._player.update(keys)
        self._camera.update(self._player.pixel_position)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._tile_map is None:
            self._init()

        screen.fill((0, 0, 0))
        self._tile_map.render(screen, self._camera.offset_x, self._camera.offset_y)
        self._player.render(screen, self._camera.offset_x, self._camera.offset_y)