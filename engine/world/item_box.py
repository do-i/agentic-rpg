# engine/world/item_box.py

from __future__ import annotations

import pygame

from engine.common.flag_state import FlagState
from engine.common.font_provider import get_fonts
from engine.world.item_box_sprite import ItemBoxSprite
from engine.world.position_data import Position

BOX_FALLBACK_COLOR = (140, 90, 30)
INDICATOR_COLOR = (255, 220, 50)


class ItemBox:
    """
    Static field treasure chest.
    - Position is tile-based; collision rect is the full tile footprint.
    - Presence is flag-gated (same semantics as Npc).
    - Opened-state lives in OpenedBoxesState on GameState — not on the box.
    - Keeps blocking the player in both opened and closed states.
    """

    def __init__(
        self,
        box_id: str,
        tile_x: int,
        tile_y: int,
        loot_items: list[tuple[str, int]],
        loot_magic_cores: list[tuple[str, int]],
        tile_size: int,
        present_requires: list[str] | None = None,
        present_excludes: list[str] | None = None,
        sprite: ItemBoxSprite | None = None,
    ) -> None:
        self.id = box_id
        self._tile_size = tile_size
        self._px = tile_x * tile_size
        self._py = tile_y * tile_size
        self.loot_items = loot_items
        self.loot_magic_cores = loot_magic_cores
        self._present_requires = present_requires or []
        self._present_excludes = present_excludes or []
        self._sprite = sprite
        self._interaction_range = tile_size * 1.5

    @property
    def pixel_position(self) -> Position:
        return Position(self._px, self._py)

    @property
    def collision_rect(self) -> tuple[int, int, int, int]:
        return (self._px, self._py, self._tile_size, self._tile_size)

    @property
    def sort_y(self) -> int:
        """Bottom of sprite — used for y-sorting in the world renderer."""
        return self._py + self._tile_size

    def is_present(self, flags: FlagState) -> bool:
        return flags.has_all(self._present_requires) and flags.has_none(self._present_excludes)

    def is_near(self, player_px: Position) -> bool:
        dx = abs(self._px - player_px.x)
        dy = abs(self._py - player_px.y)
        return dx <= self._interaction_range and dy <= self._interaction_range

    def render(
        self,
        screen: pygame.Surface,
        offset_x: int,
        offset_y: int,
        opened: bool,
        near: bool = False,
    ) -> None:
        sx = self._px - offset_x
        sy = self._py - offset_y

        if self._sprite is not None:
            frame = self._sprite.opened() if opened else self._sprite.closed()
            screen.blit(frame, (sx, sy))
        else:
            pygame.draw.rect(screen, BOX_FALLBACK_COLOR, (sx, sy, self._tile_size, self._tile_size))

        if near and not opened:
            font = get_fonts().get(18, bold=True)
            indicator = font.render("!", True, INDICATOR_COLOR)
            screen.blit(indicator, (sx + self._tile_size // 2 - indicator.get_width() // 2, sy - 22))

    def __repr__(self) -> str:
        return f"ItemBox({self.id!r}, pos=({self._px},{self._py}))"
