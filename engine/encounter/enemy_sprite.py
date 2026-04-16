# engine/encounter/enemy_sprite.py
#
# Visible enemy entity on the world map.
# Mirrors engine/world/npc.py structure but with a wander/chase state machine.

from __future__ import annotations

from typing import Literal

import pygame
from pathlib import Path

from engine.world.sprite_sheet import SpriteSheet, Direction
from engine.util.pseudo_random import PseudoRandom

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.world.collision import CollisionMap

# Sprite/render constants — identical footprint to Npc
ENEMY_SIZE            = 64
ENEMY_COLOR           = (200, 60, 60)   # red placeholder rect
ENEMY_BOSS_COLOR      = (160, 0, 200)   # purple for bosses
COLLISION_W           = 20
COLLISION_H           = 18
COLLISION_OFFSET_X    = (ENEMY_SIZE - COLLISION_W) // 2   # 22
COLLISION_OFFSET_Y    = ENEMY_SIZE - COLLISION_H - 5      # 41

# Animation
IDLE_FRAME     = 0
WALK_START     = 1
WALK_END       = 8
BASE_FRAME_DUR = 0.15   # seconds per frame

# Wander timing
WANDER_PAUSE_MIN = 1.0
WANDER_PAUSE_MAX = 3.5

_DIR_DX = {Direction.LEFT: -1, Direction.RIGHT: 1, Direction.UP: 0,  Direction.DOWN: 0}
_DIR_DY = {Direction.UP:   -1, Direction.DOWN:  1, Direction.LEFT: 0, Direction.RIGHT: 0}


def _direction_toward(ex: float, ey: float, px: float, py: float) -> Direction:
    """4-way snap: pick direction enemy should face to move toward player."""
    dx = px - ex
    dy = py - ey
    if abs(dy) >= abs(dx):
        return Direction.UP if dy < 0 else Direction.DOWN
    return Direction.LEFT if dx < 0 else Direction.RIGHT


class EnemySprite:
    """
    Visible enemy on the world map.

    Bosses are stationary (is_boss=True).
    Regular enemies wander randomly; when the player enters effective_chase_range
    tiles, they switch to chasing and move directly toward the player.

    Battle starts when the player's collision rect overlaps the enemy's.
    """

    def __init__(
        self,
        formation: list[str],         # full enemy id list; first id = visible sprite
        tile_x: int,
        tile_y: int,
        is_boss: bool = False,
        chase_range: int = 0,         # tiles; 0 = never chases
        sprite_sheet: SpriteSheet | None = None,
        rng: PseudoRandom | None = None,
        wander_range: int = 4,        # tiles from spawn
        tile_size: int = 32,
    ) -> None:
        self._tile_size     = tile_size
        self.formation      = formation
        self.is_boss        = is_boss
        self.chase_range    = chase_range

        ts = tile_size
        self._origin_px     = tile_x * ts + ts // 2 - COLLISION_OFFSET_X - COLLISION_W // 2
        self._origin_py     = tile_y * ts + ts // 2 - COLLISION_OFFSET_Y - COLLISION_H // 2
        self._px: float     = float(self._origin_px)
        self._py: float     = float(self._origin_py)

        self._rng           = rng
        self._sprite_sheet  = sprite_sheet
        self._wander_range  = wander_range
        self._move_speed    = tile_size * 1.5   # px/sec

        # Animation
        self._facing_dir    = Direction.DOWN
        self._frame_index   = IDLE_FRAME
        self._frame_timer   = 0.0

        # Wander state
        self._state: Literal["wandering", "chasing"] = "wandering"
        self._wander_target_px: int | None = None
        self._wander_target_py: int | None = None
        self._wander_pause  = self._rng.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
        self._wander_moving = False

        self.active: bool = True

    # ── Properties ────────────────────────────────────────────────

    @property
    def collision_rect(self) -> tuple[int, int, int, int]:
        return (
            int(self._px) + COLLISION_OFFSET_X,
            int(self._py) + COLLISION_OFFSET_Y,
            COLLISION_W,
            COLLISION_H,
        )

    @property
    def pixel_y(self) -> float:
        return self._py

    def deactivate(self) -> None:
        """Mark inactive and reset to spawn origin. Called when player engages in battle."""
        self.active = False
        self._px = float(self._origin_px)
        self._py = float(self._origin_py)
        self._state = "wandering"
        self._wander_moving = False
        self._wander_target_px = None
        self._wander_target_py = None
        self._wander_pause = self._rng.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)

    def activate(self) -> None:
        """Mark active. Called by EnemySpawner when the respawn interval fires."""
        self.active = True
        self._wander_pause = self._rng.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)

    def collides_with(self, rect: tuple[int, int, int, int]) -> bool:
        cx, cy, cw, ch = self.collision_rect
        rx, ry, rw, rh = rect
        return cx < rx + rw and cx + cw > rx and cy < ry + rh and cy + ch > ry

    # ── Update ────────────────────────────────────────────────────

    def update(
        self,
        delta: float,
        player_px: float,
        player_py: float,
        collision_map: CollisionMap | None,
        other_rects: list[tuple[int, int, int, int]],
        effective_chase_range: int,
    ) -> None:
        """Update movement and animation. Called every frame by EnemySpawner."""
        if self.is_boss:
            return   # bosses never move

        dist_tiles = max(
            abs(player_px - self._px),
            abs(player_py - self._py),
        ) / self._tile_size

        if effective_chase_range > 0 and dist_tiles <= effective_chase_range:
            self._state = "chasing"
            self._update_chase(delta, player_px, player_py, collision_map, other_rects)
        else:
            self._state = "wandering"
            self._update_wander(delta, collision_map, other_rects)

    def _update_chase(
        self,
        delta: float,
        player_px: float,
        player_py: float,
        collision_map: CollisionMap | None,
        other_rects: list[tuple[int, int, int, int]],
    ) -> None:
        dx = player_px - self._px
        dy = player_py - self._py
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            return

        # Update facing
        if abs(dx) >= abs(dy):
            self._facing_dir = Direction.RIGHT if dx > 0 else Direction.LEFT
        else:
            self._facing_dir = Direction.DOWN if dy > 0 else Direction.UP

        step = self._move_speed * delta
        ratio = step / dist
        new_px = self._px + dx * ratio
        new_py = self._py + dy * ratio

        if not self._is_blocked(int(new_px), int(new_py), collision_map, other_rects):
            self._px = new_px
            self._py = new_py
        self._advance_frame(delta)

    def _update_wander(
        self,
        delta: float,
        collision_map: CollisionMap | None,
        other_rects: list[tuple[int, int, int, int]],
    ) -> None:
        if not self._wander_moving:
            self._wander_pause -= delta
            self._frame_index = IDLE_FRAME
            if self._wander_pause <= 0:
                if self._pick_wander_target(collision_map, other_rects):
                    self._wander_moving = True
                else:
                    self._wander_pause = self._rng.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
            return

        tx = self._wander_target_px
        ty = self._wander_target_py
        dx = tx - self._px
        dy = ty - self._py
        dist = max(abs(dx), abs(dy))

        if dist <= self._move_speed * delta:
            if not self._is_blocked(tx, ty, collision_map, other_rects):
                self._px = tx
                self._py = ty
            self._wander_moving = False
            self._wander_pause = self._rng.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
            self._frame_index = IDLE_FRAME
            return

        if abs(dx) >= abs(dy):
            self._facing_dir = Direction.LEFT if dx < 0 else Direction.RIGHT
        else:
            self._facing_dir = Direction.UP if dy < 0 else Direction.DOWN

        move = self._move_speed * delta
        # Clamp each axis to the remaining distance to prevent overshoot oscillation.
        step_x = min(move, abs(dx)) * (1 if dx > 0 else -1) if dx != 0 else 0.0
        step_y = min(move, abs(dy)) * (1 if dy > 0 else -1) if dy != 0 else 0.0
        new_px = self._px + step_x
        new_py = self._py + step_y

        if self._is_blocked(int(new_px), int(new_py), collision_map, other_rects):
            self._wander_moving = False
            self._wander_pause = self._rng.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
            self._frame_index = IDLE_FRAME
            return

        self._px = new_px
        self._py = new_py
        self._advance_frame(delta)

    def _pick_wander_target(
        self,
        collision_map: CollisionMap | None,
        other_rects: list[tuple[int, int, int, int]],
    ) -> bool:
        max_offset = self._wander_range * self._tile_size
        for _ in range(8):
            tx = int(self._origin_px + self._rng.randint(-max_offset, max_offset))
            ty = int(self._origin_py + self._rng.randint(-max_offset, max_offset))
            if not self._is_blocked(tx, ty, collision_map, other_rects):
                self._wander_target_px = tx
                self._wander_target_py = ty
                return True
        return False

    def _is_blocked(
        self,
        px: int,
        py: int,
        collision_map: CollisionMap | None,
        other_rects: list[tuple[int, int, int, int]],
    ) -> bool:
        cx = px + COLLISION_OFFSET_X
        cy = py + COLLISION_OFFSET_Y
        if collision_map and collision_map.is_rect_blocked(cx, cy, COLLISION_W, COLLISION_H):
            return True
        for ox, oy, ow, oh in other_rects:
            if cx < ox + ow and cx + COLLISION_W > ox and cy < oy + oh and cy + COLLISION_H > oy:
                return True
        return False

    def _advance_frame(self, delta: float) -> None:
        self._frame_timer += delta
        if self._frame_timer >= BASE_FRAME_DUR:
            self._frame_timer -= BASE_FRAME_DUR
            nxt = self._frame_index + 1
            if nxt < WALK_START or nxt > WALK_END:
                nxt = WALK_START
            self._frame_index = nxt

    # ── Render ────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        sx = int(self._px) - offset_x
        sy = int(self._py) - offset_y

        if self._sprite_sheet:
            frame = self._sprite_sheet.get_frame(self._facing_dir, self._frame_index)
            scaled = pygame.transform.scale(frame, (ENEMY_SIZE, ENEMY_SIZE))
            screen.blit(scaled, (sx, sy))
        else:
            color = ENEMY_BOSS_COLOR if self.is_boss else ENEMY_COLOR
            pygame.draw.rect(screen, color, (sx, sy, ENEMY_SIZE, ENEMY_SIZE))

    def __repr__(self) -> str:
        return (
            f"EnemySprite(formation={self.formation!r}, "
            f"boss={self.is_boss}, state={self._state}, "
            f"pos=({self._px:.0f},{self._py:.0f}))"
        )
