# engine/world/portal.py

from dataclasses import dataclass
from engine.core.models.position import Position
from engine.core.settings import Settings


@dataclass
class Portal:
    """
    Represents a map exit.
    Pixel coords from TMX object layer — trigger uses pixel overlap.
    """
    x: int              # pixel x (top-left of object)
    y: int              # pixel y (top-left of object)
    width: int          # pixel width (0 for point objects)
    height: int         # pixel height (0 for point objects)
    target_map: str
    target_position: Position

    def overlaps_rect(self, rx: int, ry: int, rw: int, rh: int) -> bool:
        """
        Returns True if the given rect overlaps this portal's bounds.
        For point objects, uses a single tile area centered on the point.
        """
        # point object — treat as one tile area
        if self.width == 0 or self.height == 0:
            ts = Settings.TILE_SIZE
            px = self.x - ts // 2
            py = self.y - ts // 2
            pw = ts
            ph = ts
        else:
            px, py, pw, ph = self.x, self.y, self.width, self.height

        return (
            rx < px + pw and
            rx + rw > px and
            ry < py + ph and
            ry + rh > py
        )