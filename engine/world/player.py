# engine/world/player.py

import pygame
from engine.core.models.position import Position
from engine.core.settings import Settings
from engine.world.collision import CollisionMap
from engine.world.sprite_sheet import SpriteSheet, Direction
from engine.world.animation_controller import AnimationController

PLAYER_SPEED  = 5        # pixels per frame
PLAYER_WIDTH  = 64       # sprite render width
PLAYER_HEIGHT = 64       # sprite render height

# Collision rect — 20×20, centered horizontally, 5px from bottom
COLLISION_W = 20
COLLISION_H = 18
COLLISION_OFFSET_X = (PLAYER_WIDTH - COLLISION_W) // 2   # 22
COLLISION_OFFSET_Y = PLAYER_HEIGHT - COLLISION_H - 5     # 39

DEBUG_COLLISION = True  # toggle to show red collision rect

PLAYER_COLOR = (220, 80, 80)  # fallback placeholder color

# movement vectors — arrow keys only
DIRECTION_MAP: dict[int, tuple[int, int]] = {
    pygame.K_UP:    (0, -1),
    pygame.K_DOWN:  (0,  1),
    pygame.K_LEFT:  (-1, 0),
    pygame.K_RIGHT: (1,  0),
}


class Player:
    """
    Handles player input, position update, animation, and rendering.
    Pixel position = top-left of the 64×64 sprite.
    Collision rect = 20×20 centered horizontally, 5px from sprite bottom.
    Spawn aligns collision rect center to tile center.
    """

    def __init__(
        self,
        start: Position,
        map_width_px: int,
        map_height_px: int,
        sprite_sheet: SpriteSheet | None = None,
    ) -> None:
        # align collision rect center to tile center
        ts = Settings.TILE_SIZE
        self._x: float = float(
            start.x * ts + ts // 2 - COLLISION_OFFSET_X - COLLISION_W // 2
        )
        self._y: float = float(
            start.y * ts + ts // 2 - COLLISION_OFFSET_Y - COLLISION_H // 2
        )
        self._map_w = map_width_px
        self._map_h = map_height_px
        self._animation: AnimationController | None = (
            AnimationController(sprite_sheet) if sprite_sheet else None
        )

    @property
    def pixel_position(self) -> Position:
        """Top-left of sprite in pixel coords."""
        return Position(int(self._x), int(self._y))

    @property
    def collision_rect_position(self) -> Position:
        """Top-left of collision rect in pixel coords."""
        return Position(
            int(self._x) + COLLISION_OFFSET_X,
            int(self._y) + COLLISION_OFFSET_Y,
        )

    @property
    def tile_position(self) -> Position:
        """Tile coords derived from collision rect center."""
        cx = int(self._x) + COLLISION_OFFSET_X + COLLISION_W // 2
        cy = int(self._y) + COLLISION_OFFSET_Y + COLLISION_H // 2
        return Position(cx // Settings.TILE_SIZE, cy // Settings.TILE_SIZE)

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        collision_map: CollisionMap | None = None,
        frozen: bool = False,
    ) -> None:
        if frozen:
            if self._animation:
                self._animation.update(1 / Settings.FPS, 0, 0)
            return
        dx, dy = 0, 0
        for key, (vx, vy) in DIRECTION_MAP.items():
            if keys[key]:
                dx += vx
                dy += vy

        if self._animation:
            self._animation.update(1 / Settings.FPS, dx, dy)

        if dx == 0 and dy == 0:
            return

        # normalise diagonal speed
        if dx != 0 and dy != 0:
            factor = 0.7071  # 1 / sqrt(2)
            dx_move = dx * factor * PLAYER_SPEED
            dy_move = dy * factor * PLAYER_SPEED
        else:
            dx_move = dx * PLAYER_SPEED
            dy_move = dy * PLAYER_SPEED

        new_x = self._x + dx_move
        new_y = self._y + dy_move

        # clamp to map bounds using collision rect edges
        new_x = max(
            float(-COLLISION_OFFSET_X),
            min(new_x, float(self._map_w - COLLISION_OFFSET_X - COLLISION_W))
        )
        new_y = max(
            float(-COLLISION_OFFSET_Y),
            min(new_y, float(self._map_h - COLLISION_OFFSET_Y - COLLISION_H))
        )

        if collision_map:
            col_x = int(new_x) + COLLISION_OFFSET_X
            col_y = int(new_y) + COLLISION_OFFSET_Y
            if collision_map.is_rect_blocked(col_x, col_y, COLLISION_W, COLLISION_H):
                return

        self._x = new_x
        self._y = new_y

    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        screen_x = int(self._x) - offset_x
        screen_y = int(self._y) - offset_y

        if self._animation:
            frame = self._animation.current_frame
            scaled = pygame.transform.scale(frame, (PLAYER_WIDTH, PLAYER_HEIGHT))
            screen.blit(scaled, (screen_x, screen_y))
        else:
            pygame.draw.rect(
                screen,
                PLAYER_COLOR,
                (screen_x, screen_y, PLAYER_WIDTH, PLAYER_HEIGHT),
            )

        if DEBUG_COLLISION:
            col_x = int(self._x) + COLLISION_OFFSET_X - offset_x
            col_y = int(self._y) + COLLISION_OFFSET_Y - offset_y
            pygame.draw.rect(screen, (255, 0, 0), (col_x, col_y, COLLISION_W, COLLISION_H), 2)