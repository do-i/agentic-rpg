# engine/world/portal.py

from dataclasses import dataclass
from engine.core.models.position import Position
from engine.core.settings import Settings


@dataclass
class Portal:
    """
    Represents a map exit.
    Pixel coords from TMX object layer — trigger is tile-based.
    """
    x: int              # pixel x (top-left of object)
    y: int              # pixel y (top-left of object)
    width: int          # pixel width (0 for point objects)
    height: int         # pixel height (0 for point objects)
    target_map: str
    target_position: Position

    def contains_tile(self, tile_x: int, tile_y: int) -> bool:
        """
        Returns True if the given tile coordinate falls within this portal.
        Converts portal pixel bounds to tile bounds for comparison.
        """
        ts = Settings.TILE_SIZE

        # point object — match exact tile
        if self.width == 0 or self.height == 0:
            portal_tx = self.x // ts
            portal_ty = self.y // ts
            return tile_x == portal_tx and tile_y == portal_ty

        # rect object — match any tile within bounds
        left   = self.x // ts
        top    = self.y // ts
        right  = (self.x + self.width - 1) // ts
        bottom = (self.y + self.height - 1) // ts
        return left <= tile_x <= right and top <= tile_y <= bottom
