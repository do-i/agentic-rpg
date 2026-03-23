# engine/world/npc.py

import pygame
from pathlib import Path
from engine.core.models.position import Position
from engine.core.state.flag_state import FlagState
from engine.core.settings import Settings
from engine.world.sprite_sheet import SpriteSheet, Direction

NPC_SIZE = 24
NPC_COLOR = (80, 160, 220)
INDICATOR_COLOR = (255, 220, 50)
INTERACTION_RANGE = Settings.TILE_SIZE * 1.5  # pixels

FRAME_INDEX = 0  # always idle frame

_FACING_MAP = {
    "up":    Direction.UP,
    "down":  Direction.DOWN,
    "left":  Direction.LEFT,
    "right": Direction.RIGHT,
}


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
    When player is nearby, NPC faces the player (4-way snap).
    Falls back to colored rect if no sprite is loaded.
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
    ) -> None:
        self.id = npc_id
        self.dialogue_id = dialogue_id
        self._px = tile_x * Settings.TILE_SIZE
        self._py = tile_y * Settings.TILE_SIZE
        self._present_requires = present_requires or []
        self._present_excludes = present_excludes or []
        self._sprite_sheet = sprite_sheet
        self._default_facing: Direction = _FACING_MAP.get(default_facing, Direction.DOWN)

    @property
    def pixel_position(self) -> Position:
        return Position(self._px, self._py)

    def is_present(self, flags: FlagState) -> bool:
        return flags.has_all(self._present_requires) and flags.has_none(self._present_excludes)

    def is_near(self, player_px: Position) -> bool:
        dx = abs(self._px - player_px.x)
        dy = abs(self._py - player_px.y)
        return dx <= INTERACTION_RANGE and dy <= INTERACTION_RANGE

    def _facing(self, player_pos: Position | None, near: bool) -> Direction:
        if near and player_pos is not None:
            return _direction_toward(self._px, self._py, player_pos)
        return self._default_facing

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
            frame = self._sprite_sheet.get_frame(direction, FRAME_INDEX)
            # scale 64x64 → 32x64 to match player rendering
            scaled = pygame.transform.scale(frame, (32, 64))
            screen.blit(scaled, (sx, sy))
        else:
            pygame.draw.rect(screen, NPC_COLOR, (sx, sy, NPC_SIZE, NPC_SIZE))

        if near:
            font = pygame.font.SysFont("Arial", 18, bold=True)
            indicator = font.render("!", True, INDICATOR_COLOR)
            screen.blit(indicator, (sx + 16 - indicator.get_width() // 2, sy - 22))

    def __repr__(self) -> str:
        return f"Npc({self.id!r}, dialogue={self.dialogue_id!r}, pos=({self._px},{self._py}))"
