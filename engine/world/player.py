# engine/world/player.py

import pygame
from engine.world.position_data import Position
from engine.world.collision import CollisionMap
from engine.world.sprite_sheet import Direction, SpriteSheet
from engine.world.animation_controller import AnimationController

# Fallback defaults — authoritative values live in scenario balance YAML
# / engine settings; injected via Player.__init__.
PLAYER_SPEED    = 5
DEBUG_COLLISION = False

PLAYER_WIDTH  = 64
PLAYER_HEIGHT = 64

COLLISION_W = 20
COLLISION_H = 18
COLLISION_OFFSET_X = (PLAYER_WIDTH  - COLLISION_W) // 2   # 22
COLLISION_OFFSET_Y =  PLAYER_HEIGHT - COLLISION_H  - 5    # 41

PLAYER_COLOR    = (220, 80, 80)

DIRECTION_MAP: dict[int, tuple[int, int]] = {
    pygame.K_UP:    (0, -1),
    pygame.K_DOWN:  (0,  1),
    pygame.K_LEFT:  (-1, 0),
    pygame.K_RIGHT: (1,  0),
}


def _rects_overlap(ax: int, ay: int, aw: int, ah: int,
                   bx: int, by: int, bw: int, bh: int) -> bool:
    return (ax < bx + bw and ax + aw > bx and
            ay < by + bh and ay + ah > by)


def _tile_blocked(px: float, py: float,
                  collision_map: CollisionMap | None) -> bool:
    """True if player rect at (px, py) overlaps a tile collision."""
    if collision_map is None:
        return False
    cx = int(px) + COLLISION_OFFSET_X
    cy = int(py) + COLLISION_OFFSET_Y
    return collision_map.is_rect_blocked(cx, cy, COLLISION_W, COLLISION_H)


def _npc_blocked(px: float, py: float,
                 npc_rects: list[tuple[int, int, int, int]]) -> bool:
    """True if player rect at (px, py) overlaps any NPC collision rect."""
    cx = int(px) + COLLISION_OFFSET_X
    cy = int(py) + COLLISION_OFFSET_Y
    for (nx, ny, nw, nh) in npc_rects:
        if _rects_overlap(cx, cy, COLLISION_W, COLLISION_H, nx, ny, nw, nh):
            return True
    return False


class Player:
    """
    Wall collision — axis-separation sliding:
      1. Try full move (dx, dy).
      2. If tile-blocked, try X-only (dx, 0).
      3. If tile-blocked, try Y-only (0, dy).
      4. Both blocked — stay put.

    NPC collision — hard block applied on top of every candidate position.
    NPC rects never slide; they always stop the player dead.

    smooth_collision=False skips axis-separation; any tile block stops dead too.

    Controlled via engine/settings/settings.yaml:
        movement:
          smooth_collision: true
    """

    def __init__(
        self,
        start: Position,
        map_width_px: int,
        map_height_px: int,
        sprite_sheet: SpriteSheet | None = None,
        smooth_collision: bool = True,
        tile_size: int = 32,
        fps: int = 60,
        player_speed: int = PLAYER_SPEED,
        debug_collision: bool = DEBUG_COLLISION,
    ) -> None:
        self._tile_size = tile_size
        self._fps = fps
        self._speed = player_speed
        self._debug_collision = debug_collision
        ts = tile_size
        self._x: float = float(
            start.x * ts + ts // 2 - COLLISION_OFFSET_X - COLLISION_W // 2
        )
        self._y: float = float(
            start.y * ts + ts // 2 - COLLISION_OFFSET_Y - COLLISION_H // 2
        )
        self._map_w = map_width_px
        self._map_h = map_height_px
        self._smooth = smooth_collision
        self._animation: AnimationController | None = (
            AnimationController(sprite_sheet) if sprite_sheet else None
        )

    # ── Properties ────────────────────────────────────────────

    @property
    def pixel_position(self) -> Position:
        return Position(int(self._x), int(self._y))

    @property
    def collision_rect_position(self) -> Position:
        return Position(int(self._x) + COLLISION_OFFSET_X,
                        int(self._y) + COLLISION_OFFSET_Y)

    @property
    def facing_direction(self) -> Direction:
        if self._animation:
            return self._animation.direction
        return Direction.DOWN

    @property
    def tile_position(self) -> Position:
        cx = int(self._x) + COLLISION_OFFSET_X + COLLISION_W // 2
        cy = int(self._y) + COLLISION_OFFSET_Y + COLLISION_H // 2
        return Position(cx // self._tile_size, cy // self._tile_size)

    # ── Update ────────────────────────────────────────────────

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        collision_map: CollisionMap | None = None,
        frozen: bool = False,
        npc_rects: list[tuple[int, int, int, int]] | None = None,
    ) -> None:
        if frozen:
            if self._animation:
                self._animation.update(1 / self._fps, 0, 0)
            return

        dx, dy = 0, 0
        for key, (vx, vy) in DIRECTION_MAP.items():
            if keys[key]:
                dx += vx
                dy += vy

        if self._animation:
            self._animation.update(1 / self._fps, dx, dy)

        if dx == 0 and dy == 0:
            return

        # normalise diagonal speed
        if dx != 0 and dy != 0:
            factor = 0.7071
            dx_move = dx * factor * self._speed
            dy_move = dy * factor * self._speed
        else:
            dx_move = dx * self._speed
            dy_move = dy * self._speed

        npc_rects = npc_rects or []

        if self._smooth:
            self._move_smooth(dx_move, dy_move, collision_map, npc_rects)
        else:
            self._move_hard(dx_move, dy_move, collision_map, npc_rects)

    # ── Movement strategies ───────────────────────────────────

    def _clamp(self, x: float, y: float) -> tuple[float, float]:
        x = max(float(-COLLISION_OFFSET_X),
                min(x, float(self._map_w - COLLISION_OFFSET_X - COLLISION_W)))
        y = max(float(-COLLISION_OFFSET_Y),
                min(y, float(self._map_h - COLLISION_OFFSET_Y - COLLISION_H)))
        return x, y

    def _move_hard(self, dx: float, dy: float,
                   collision_map: CollisionMap | None,
                   npc_rects: list) -> None:
        """Hard block — stop dead on any tile or NPC overlap."""
        new_x, new_y = self._clamp(self._x + dx, self._y + dy)
        if _tile_blocked(new_x, new_y, collision_map):
            return
        if _npc_blocked(new_x, new_y, npc_rects):
            return
        self._x, self._y = new_x, new_y

    def _move_smooth(self, dx: float, dy: float,
                     collision_map: CollisionMap | None,
                     npc_rects: list) -> None:
        """
        Axis-separation sliding against tile collisions.
        NPC collision is always a hard block — no sliding around NPCs.

        Order:
          1. Try full (dx, dy)   — NPC hard block applied here too.
          2. If tile-blocked, try X-only (dx, 0).
          3. If tile-blocked, try Y-only (0, dy).
          4. Both blocked — stay put.
        """
        # ── Attempt 1: full move ──────────────────────────────
        new_x, new_y = self._clamp(self._x + dx, self._y + dy)
        if _npc_blocked(new_x, new_y, npc_rects):
            return   # NPC in the way — hard stop, no slide
        if not _tile_blocked(new_x, new_y, collision_map):
            self._x, self._y = new_x, new_y
            return

        # ── Attempt 2: X-only slide ───────────────────────────
        new_x, new_y = self._clamp(self._x + dx, self._y)
        if not _npc_blocked(new_x, new_y, npc_rects) and \
           not _tile_blocked(new_x, new_y, collision_map):
            self._x, self._y = new_x, new_y
            return

        # ── Attempt 3: Y-only slide ───────────────────────────
        new_x, new_y = self._clamp(self._x, self._y + dy)
        if not _npc_blocked(new_x, new_y, npc_rects) and \
           not _tile_blocked(new_x, new_y, collision_map):
            self._x, self._y = new_x, new_y

        # ── Attempt 4: stay put ───────────────────────────────

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        screen_x = int(self._x) - offset_x
        screen_y = int(self._y) - offset_y

        if self._animation:
            frame  = self._animation.current_frame
            scaled = pygame.transform.scale(frame, (PLAYER_WIDTH, PLAYER_HEIGHT))
            screen.blit(scaled, (screen_x, screen_y))
        else:
            pygame.draw.rect(screen, PLAYER_COLOR,
                             (screen_x, screen_y, PLAYER_WIDTH, PLAYER_HEIGHT))

        if self._debug_collision:
            col_x = int(self._x) + COLLISION_OFFSET_X - offset_x
            col_y = int(self._y) + COLLISION_OFFSET_Y - offset_y
            pygame.draw.rect(screen, (255, 0, 0),
                             (col_x, col_y, COLLISION_W, COLLISION_H), 2)
