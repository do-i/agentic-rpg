# engine/world/camera.py

from __future__ import annotations

from engine.world.position_data import Position


class Camera:
    """
    Tracks viewport offset — keeps player centered,
    clamped to map bounds.
    """

    def __init__(
        self,
        map_width_px: int,
        map_height_px: int,
        screen_width: int,
        screen_height: int,
    ) -> None:
        self._map_w = map_width_px
        self._map_h = map_height_px
        self._screen_w = screen_width
        self._screen_h = screen_height
        self.offset_x: int = 0
        self.offset_y: int = 0

    def update(self, player_pos: Position) -> None:
        """Recalculate offset so player stays centered."""
        cx = player_pos.x - self._screen_w // 2
        cy = player_pos.y - self._screen_h // 2
        self.offset_x = max(0, min(cx, self._map_w - self._screen_w))
        self.offset_y = max(0, min(cy, self._map_h - self._screen_h))

    def apply(self, x: int, y: int) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        return x - self.offset_x, y - self.offset_y

    def __repr__(self) -> str:
        return f"Camera(offset=({self.offset_x}, {self.offset_y}))"
