# engine/world/sign.py

from __future__ import annotations

import pygame

from engine.common.font_provider import get_fonts
from engine.world.position_data import Position

INDICATOR_COLOR = (255, 220, 50)


class Sign:
    """
    A readable "message board" anchored to a sign tile already painted on the
    map. The tile art and its collision are owned by the TMX layers; this object
    only carries the interaction: presence near the player, and the dialogue id
    to play when the player reads it.

    Signs are not flag-gated and have no sprite of their own — the tile renders
    itself. The only thing drawn here is the "!" prompt when the player stands
    next to a sign and faces it, matching NPCs and item boxes.
    """

    def __init__(
        self,
        sign_id: str,
        dialogue_id: str,
        tile_x: int,
        tile_y: int,
        tile_size: int,
    ) -> None:
        self.id = sign_id
        self.dialogue_id = dialogue_id
        self._tile_size = tile_size
        self._px = tile_x * tile_size
        self._py = tile_y * tile_size
        self._interaction_range = tile_size * 1.5

    @property
    def pixel_position(self) -> Position:
        return Position(self._px, self._py)

    @property
    def sort_y(self) -> int:
        """Bottom of the tile — used for y-sorting in the world renderer."""
        return self._py + self._tile_size

    def is_near(self, player_px: Position) -> bool:
        dx = abs(self._px - player_px.x)
        dy = abs(self._py - player_px.y)
        return dx <= self._interaction_range and dy <= self._interaction_range

    def render(
        self,
        screen: pygame.Surface,
        offset_x: int,
        offset_y: int,
        near: bool = False,
    ) -> None:
        if not near:
            return
        sx = self._px - offset_x
        sy = self._py - offset_y
        font = get_fonts().get(18, bold=True)
        indicator = font.render("!", True, INDICATOR_COLOR)
        screen.blit(indicator, (sx + self._tile_size // 2 - indicator.get_width() // 2, sy - 22))

    def __repr__(self) -> str:
        return f"Sign({self.id!r}, dialogue={self.dialogue_id!r}, pos=({self._px},{self._py}))"
