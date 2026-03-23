# engine/world/player.py
#
# STUB — sprite is a coloured rectangle. Full spritesheet in Phase 2.

import pygame
from engine.core.models.position import Position
from engine.core.settings import Settings
from engine.world.collision import CollisionMap

PLAYER_SPEED = 3        # pixels per frame
PLAYER_SIZE  = 24       # placeholder rectangle size
PLAYER_COLOR = (220, 80, 80)

# 8-direction movement vectors — arrow keys only
DIRECTION_MAP: dict[int, tuple[int, int]] = {
    pygame.K_UP:    (0, -1),
    pygame.K_DOWN:  (0,  1),
    pygame.K_LEFT:  (-1, 0),
    pygame.K_RIGHT: (1,  0),
}


class Player:
    """
    Handles player input, position update, and placeholder rendering.
    Position stored in pixel coordinates.
    """

    def __init__(self, start: Position, map_width_px: int, map_height_px: int) -> None:
        # convert tile position → pixel coordinates
        self._x: float = float(start.x * Settings.TILE_SIZE)
        self._y: float = float(start.y * Settings.TILE_SIZE)
        self._map_w = map_width_px
        self._map_h = map_height_px

    @property
    def pixel_position(self) -> Position:
        return Position(int(self._x), int(self._y))

    def update(self, keys: pygame.key.ScancodeWrapper, collision_map: CollisionMap | None = None) -> None:
        dx, dy = 0, 0
        for key, (vx, vy) in DIRECTION_MAP.items():
            if keys[key]:
                dx += vx
                dy += vy

        if dx == 0 and dy == 0:
            return

        # normalise diagonal speed
        if dx != 0 and dy != 0:
            factor = 0.7071  # 1 / sqrt(2)
            dx *= factor
            dy *= factor

        new_x = self._x + dx * PLAYER_SPEED
        new_y = self._y + dy * PLAYER_SPEED

        new_x = max(0.0, min(new_x, float(self._map_w - PLAYER_SIZE)))
        new_y = max(0.0, min(new_y, float(self._map_h - PLAYER_SIZE)))

        if collision_map and collision_map.is_rect_blocked(int(new_x), int(new_y), PLAYER_SIZE, PLAYER_SIZE):
            return  # ← stop completely

        self._x = new_x
        self._y = new_y

    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        """Phase 1 — coloured rectangle placeholder."""
        screen_x = int(self._x) - offset_x
        screen_y = int(self._y) - offset_y
        pygame.draw.rect(
            screen,
            PLAYER_COLOR,
            (screen_x, screen_y, PLAYER_SIZE, PLAYER_SIZE),
        )