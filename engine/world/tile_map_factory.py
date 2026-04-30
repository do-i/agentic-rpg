# engine/world/tile_map_factory.py

from __future__ import annotations

from engine.world.tile_map import TileMap


class TileMapFactory:
    """
    Factory for creating TileMap instances.
    Injected into scenes — decouples scene from direct TileMap construction.
    """

    def create(self, tmx_path: str) -> TileMap:
        return TileMap(tmx_path)
