# engine/world/npc.py

import random
import pygame
from pathlib import Path
from engine.core.models.position import Position
from engine.core.state.flag_state import FlagState
from engine.core.settings import Settings
from engine.world.sprite_sheet import SpriteSheet, Direction

NPC_SIZE = 64
NPC_COLOR = (80, 160, 220)
INDICATOR_COLOR = (255, 220, 50)
INTERACTION_RANGE = Settings.TILE_SIZE * 1.5  # pixels

# Animation frames
IDLE_FRAME     = 0
WALK_START     = 1
WALK_END       = 8
BASE_FRAME_DUR = 0.15  # seconds per frame at speed 1.0

# Wander timing
WANDER_PAUSE_MIN = 1.0   # seconds between moves
WANDER_PAUSE_MAX = 3.5

# Collision rect — same footprint convention as player
NPC_COLLISION_W = 20
NPC_COLLISION_H = 18
NPC_COLLISION_OFFSET_X = (NPC_SIZE - NPC_COLLISION_W) // 2   # 22
NPC_COLLISION_OFFSET_Y = NPC_SIZE - NPC_COLLISION_H - 5      # 41

_FACING_MAP = {
    "up":    Direction.UP,
    "down":  Direction.DOWN,
    "left":  Direction.LEFT,
    "right": Direction.RIGHT,
}

_DIR_DX = {Direction.LEFT: -1, Direction.RIGHT: 1, Direction.UP: 0, Direction.DOWN: 0}
_DIR_DY = {Direction.UP: -1, Direction.DOWN: 1, Direction.LEFT: 0, Direction.RIGHT: 0}


def _direction_toward(npc_px: int, npc_py: int, player: Position) -> Direction:
    """4-way snap: dominant axis wins."""
    dx = player.x - npc_px
    dy = player.y - npc_py
    if abs(dy) >= abs(dx):
        return Direction.UP if dy < 0 else Direction.DOWN
    return Direction.LEFT if dx < 0 else Direction.RIGHT


class Npc:
    """
    Represents a single NPC on the map.
    Presence is flag-gated. Interaction triggers dialogue.
    Exposes a collision rect so the player cannot walk through.
    When player is nearby, NPC faces the player (4-way snap).
    Falls back to colored rect if no sprite is loaded.

    Animation modes (configured via YAML):
      still  — static idle frame (default, legacy behavior)
      step   — cycles walk frames in place
      wander — moves randomly within range tiles of origin
    """

    def __init__(
        self,
        npc_id: str,
        dialogue_id: str,
        tile_x: int,
        tile_y: int,
        present_requires: list[str] | None = None,
        present_excludes: list[str] | None = None,
        sprite_sheet: SpriteSheet | None = None,
        default_facing: str = "down",
        anim_mode: str = "still",
        anim_speed: float = 1.0,
        wander_range: int = 2,
    ) -> None:
        self.id = npc_id
        self.dialogue_id = dialogue_id
        self._origin_px = tile_x * Settings.TILE_SIZE
        self._origin_py = tile_y * Settings.TILE_SIZE
        self._px = self._origin_px
        self._py = self._origin_py
        self._present_requires = present_requires or []
        self._present_excludes = present_excludes or []
        self._sprite_sheet = sprite_sheet
        self._default_facing: Direction = _FACING_MAP.get(default_facing, Direction.DOWN)

        # animation
        self._anim_mode = anim_mode       # still | step | wander
        self._anim_speed = anim_speed     # frame speed multiplier
        self._wander_range = wander_range # tiles from origin
        self._frame_index = IDLE_FRAME
        self._frame_timer = 0.0
        self._facing_dir = self._default_facing

        # wander state
        self._wander_target_px: int | None = None
        self._wander_target_py: int | None = None
        self._wander_pause = random.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
        self._wander_moving = False
        self._move_speed = Settings.TILE_SIZE * 1.5  # pixels/sec base

    @property
    def pixel_position(self) -> Position:
        return Position(self._px, self._py)

    @property
    def collision_rect(self) -> tuple[int, int, int, int]:
        """Returns (x, y, w, h) of NPC collision box in world pixels."""
        return (
            self._px + NPC_COLLISION_OFFSET_X,
            self._py + NPC_COLLISION_OFFSET_Y,
            NPC_COLLISION_W,
            NPC_COLLISION_H,
        )

    def is_present(self, flags: FlagState) -> bool:
        return flags.has_all(self._present_requires) and flags.has_none(self._present_excludes)

    def is_near(self, player_px: Position) -> bool:
        dx = abs(self._px - player_px.x)
        dy = abs(self._py - player_px.y)
        return dx <= INTERACTION_RANGE and dy <= INTERACTION_RANGE

    def _facing(self, player_pos: Position | None, near: bool) -> Direction:
        if near and player_pos is not None:
            return _direction_toward(self._px, self._py, player_pos)
        return self._facing_dir

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float, near: bool = False) -> None:
        """Call each frame. Advances animation and wander movement."""
        if self._anim_mode == "still":
            return

        # freeze animation when player is near (NPC faces player)
        if near:
            self._frame_index = IDLE_FRAME
            self._wander_moving = False
            self._wander_pause = random.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
            return

        if self._anim_mode == "step":
            self._update_step(delta)
        elif self._anim_mode == "wander":
            self._update_wander(delta)

    def _update_step(self, delta: float) -> None:
        """Cycle walk frames in place."""
        self._advance_frame(delta)

    def _update_wander(self, delta: float) -> None:
        """Move randomly within range, then pause."""
        if not self._wander_moving:
            self._wander_pause -= delta
            # step in place while paused
            self._frame_index = IDLE_FRAME
            self._facing_dir = self._default_facing
            if self._wander_pause <= 0:
                self._pick_wander_target()
                self._wander_moving = True
            return

        # move toward target
        tx = self._wander_target_px
        ty = self._wander_target_py
        dx = tx - self._px
        dy = ty - self._py
        dist = max(abs(dx), abs(dy))
        speed = self._move_speed * self._anim_speed

        if dist <= speed * delta:
            self._px = tx
            self._py = ty
            self._wander_moving = False
            self._wander_pause = random.uniform(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX)
            self._frame_index = IDLE_FRAME
            return

        # update facing
        if abs(dx) >= abs(dy):
            self._facing_dir = Direction.LEFT if dx < 0 else Direction.RIGHT
        else:
            self._facing_dir = Direction.UP if dy < 0 else Direction.DOWN

        # move
        move = speed * delta
        if dx != 0:
            self._px += int(move * (1 if dx > 0 else -1))
        if dy != 0:
            self._py += int(move * (1 if dy > 0 else -1))

        self._advance_frame(delta)

    def _pick_wander_target(self) -> None:
        """Choose a random tile within wander_range of origin."""
        tile_size = Settings.TILE_SIZE
        max_offset = self._wander_range * tile_size
        self._wander_target_px = self._origin_px + random.randint(-max_offset, max_offset)
        self._wander_target_py = self._origin_py + random.randint(-max_offset, max_offset)

    def _advance_frame(self, delta: float) -> None:
        """Cycle through walk frames."""
        frame_dur = BASE_FRAME_DUR / max(self._anim_speed, 0.1)
        self._frame_timer += delta
        if self._frame_timer >= frame_dur:
            self._frame_timer -= frame_dur
            nxt = self._frame_index + 1
            if nxt < WALK_START or nxt > WALK_END:
                nxt = WALK_START
            self._frame_index = nxt

    # ── Render ────────────────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        offset_x: int,
        offset_y: int,
        near: bool = False,
        player_pos: Position | None = None,
    ) -> None:
        sx = self._px - offset_x
        sy = self._py - offset_y

        if self._sprite_sheet:
            direction = self._facing(player_pos, near)
            frame = self._sprite_sheet.get_frame(direction, self._frame_index)
            scaled = pygame.transform.scale(frame, (64, 64))
            screen.blit(scaled, (sx, sy))
        else:
            pygame.draw.rect(screen, NPC_COLOR, (sx, sy, NPC_SIZE, NPC_SIZE))

        if near:
            font = pygame.font.SysFont("Arial", 18, bold=True)
            indicator = font.render("!", True, INDICATOR_COLOR)
            screen.blit(indicator, (sx + 16 - indicator.get_width() // 2, sy - 22))

    def __repr__(self) -> str:
        return f"Npc({self.id!r}, dialogue={self.dialogue_id!r}, pos=({self._px},{self._py}))"
