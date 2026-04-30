# engine/dto/portal.py

from __future__ import annotations

from dataclasses import dataclass
from engine.world.position_data import Position


@dataclass(frozen=True)
class Portal:
    """
    Represents a map exit.
    Trigger: player collision rect overlaps the portal's bounding box.
    """
    x: int              # pixel x (top-left of object)
    y: int              # pixel y (top-left of object)
    width: int          # pixel width (0 for point objects)
    height: int         # pixel height (0 for point objects)
    target_map: str
    target_position: Position

    @property
    def center_x(self) -> int:
        if self.width == 0:
            return self.x
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        if self.height == 0:
            return self.y
        return self.y + self.height // 2

    def is_triggered_by(self, col_x: int, col_y: int, col_w: int, col_h: int) -> bool:
        """
        Returns True if the player's collision rect overlaps (or touches the
        edge of) the portal's bounding box.
        """
        return (
            col_x <= self.x + self.width
            and col_x + col_w >= self.x
            and col_y <= self.y + self.height
            and col_y + col_h >= self.y
        )