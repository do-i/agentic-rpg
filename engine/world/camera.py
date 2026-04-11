# engine/world/camera.py

from engine.common.position_data import Position
from engine.settings import Settings


class Camera:
    """
    Tracks viewport offset — keeps player centered,
    clamped to map bounds.
    """

    def __init__(self, map_width_px: int, map_height_px: int) -> None:
        self._map_w = map_width_px
        self._map_h = map_height_px
        self.offset_x: int = 0
        self.offset_y: int = 0

    def update(self, player_pos: Position) -> None:
        """Recalculate offset so player stays centered."""
        cx = player_pos.x - Settings.SCREEN_WIDTH // 2
        cy = player_pos.y - Settings.SCREEN_HEIGHT // 2
        self.offset_x = max(0, min(cx, self._map_w - Settings.SCREEN_WIDTH))
        self.offset_y = max(0, min(cy, self._map_h - Settings.SCREEN_HEIGHT))

    def apply(self, x: int, y: int) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        return x - self.offset_x, y - self.offset_y

    def __repr__(self) -> str:
        return f"Camera(offset=({self.offset_x}, {self.offset_y}))"
