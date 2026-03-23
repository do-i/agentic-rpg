# engine/world/animation_controller.py

import pygame
from engine.world.sprite_sheet import SpriteSheet, Direction

FRAME_DURATION = 0.1  # seconds per frame (matches TSX duration="100")
IDLE_FRAME = 0
WALK_FRAME_START = 1
WALK_FRAME_END = 8


class AnimationController:
    """
    Tracks current direction and advances frame on timer.
    col 0 = idle (standing), cols 1-8 = walk cycle.
    Key released → immediately resets to frame 0 (idle).
    """

    def __init__(self, sprite_sheet: SpriteSheet) -> None:
        self._sheet = sprite_sheet
        self._direction = Direction.DOWN
        self._frame_index: int = IDLE_FRAME
        self._timer: float = 0.0
        self._moving: bool = False

    def update(self, delta: float, dx: int, dy: int) -> None:
        """
        Call each frame with movement delta.
        dx/dy are -1, 0, or 1 — raw direction input.
        """
        self._moving = (dx != 0 or dy != 0)

        if self._moving:
            self._update_direction(dx, dy)
            # start walk cycle at frame 1 if coming from idle
            if self._frame_index == IDLE_FRAME:
                self._frame_index = WALK_FRAME_START
            self._timer += delta
            if self._timer >= FRAME_DURATION:
                self._timer -= FRAME_DURATION
                next_frame = self._frame_index + 1
                if next_frame > WALK_FRAME_END:
                    next_frame = WALK_FRAME_START
                self._frame_index = next_frame
        else:
            self._frame_index = IDLE_FRAME
            self._timer = 0.0

    def _update_direction(self, dx: int, dy: int) -> None:
        # vertical takes priority over horizontal
        if dy < 0:
            self._direction = Direction.UP
        elif dy > 0:
            self._direction = Direction.DOWN
        elif dx < 0:
            self._direction = Direction.LEFT
        elif dx > 0:
            self._direction = Direction.RIGHT

    @property
    def current_frame(self) -> pygame.Surface:
        return self._sheet.get_frame(self._direction, self._frame_index)

    @property
    def direction(self) -> Direction:
        return self._direction

    def __repr__(self) -> str:
        return (
            f"AnimationController("
            f"direction={self._direction.name}, "
            f"frame={self._frame_index}, "
            f"moving={self._moving})"
        )