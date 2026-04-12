# engine/world/collision.py

import pytmx
from engine.common.position_data import Position

COLLISION_LAYER_NAME = "collision"


class CollisionMap:
    """
    Reads the 'collision' layer from a loaded TMX map.
    Any non-zero tile GID in that layer = impassable.
    """

    def __init__(self, tmx_data: pytmx.TiledMap, tile_size: int = 32) -> None:
        self._tile_size = tile_size
        self._blocked: set[tuple[int, int]] = set()
        self._load(tmx_data)

    def _load(self, tmx_data: pytmx.TiledMap) -> None:
        for layer in tmx_data.layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            if layer.name != COLLISION_LAYER_NAME:
                continue
            for x, y, gid in layer:
                if gid:
                    self._blocked.add((x, y))

    def is_blocked(self, tile_x: int, tile_y: int) -> bool:
        return (tile_x, tile_y) in self._blocked

    def is_blocked_px(self, px: int, py: int) -> bool:
        """Check passability using pixel coordinates."""
        tile_x = px // self._tile_size
        tile_y = py // self._tile_size
        return self.is_blocked(tile_x, tile_y)

    def is_rect_blocked(self, px: int, py: int, width: int, height: int) -> bool:
        """
        Check all four corners of a bounding box.
        Prevents clipping through walls on diagonal movement.
        """
        corners = [
            (px,             py),
            (px + width - 1, py),
            (px,             py + height - 1),
            (px + width - 1, py + height - 1),
        ]
        return any(self.is_blocked_px(cx, cy) for cx, cy in corners)

    def __repr__(self) -> str:
        return f"CollisionMap(blocked_tiles={len(self._blocked)})"
