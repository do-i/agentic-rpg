# engine/world/collision.py

import pytmx
from engine.dto.position import Position
from engine.settings import Settings

COLLISION_LAYER_NAME = "collision"


class CollisionMap:
    """
    Reads the 'collision' layer from a loaded TMX map.
    Any non-zero tile GID in that layer = impassable.
    """

    def __init__(self, tmx_data: pytmx.TiledMap) -> None:
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
        tile_x = px // Settings.TILE_SIZE
        tile_y = py // Settings.TILE_SIZE
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
