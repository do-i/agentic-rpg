# engine/dto/portal.py

from dataclasses import dataclass
from engine.common.position_data import Position
from engine.settings import Settings

PORTAL_TRIGGER_RADIUS = 8  # px — portal fires when centers are within this distance


@dataclass(frozen=True)
class Portal:
    """
    Represents a map exit.
    Trigger: portal center within PORTAL_TRIGGER_RADIUS of collision rect center.
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
        Returns True if portal center is within PORTAL_TRIGGER_RADIUS
        of the collision rect center.
        """
        ccx = col_x + col_w // 2
        ccy = col_y + col_h // 2
        dx = abs(self.center_x - ccx)
        dy = abs(self.center_y - ccy)
        return dx <= PORTAL_TRIGGER_RADIUS and dy <= PORTAL_TRIGGER_RADIUS