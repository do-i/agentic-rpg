# engine/world/npc.py

import pygame
from engine.core.models.position import Position
from engine.core.state.flag_state import FlagState
from engine.core.settings import Settings

NPC_SIZE = 24
NPC_COLOR = (80, 160, 220)
INDICATOR_COLOR = (255, 220, 50)
INTERACTION_RANGE = Settings.TILE_SIZE * 1.5  # pixels


class Npc:
    """
    Represents a single NPC on the map.
    Presence is flag-gated. Interaction triggers dialogue.
    """

    def __init__(
        self,
        npc_id: str,
        dialogue_id: str,
        tile_x: int,
        tile_y: int,
        present_requires: list[str] | None = None,
        present_excludes: list[str] | None = None,
    ) -> None:
        self.id = npc_id
        self.dialogue_id = dialogue_id
        self._px = tile_x * Settings.TILE_SIZE
        self._py = tile_y * Settings.TILE_SIZE
        self._present_requires = present_requires or []
        self._present_excludes = present_excludes or []

    @property
    def pixel_position(self) -> Position:
        return Position(self._px, self._py)

    def is_present(self, flags: FlagState) -> bool:
        return flags.has_all(self._present_requires) and flags.has_none(self._present_excludes)

    def is_near(self, player_px: Position) -> bool:
        dx = abs(self._px - player_px.x)
        dy = abs(self._py - player_px.y)
        return dx <= INTERACTION_RANGE and dy <= INTERACTION_RANGE

    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int, near: bool = False) -> None:
        """Phase 2 — colored rect placeholder. Phase 5: spritesheet."""
        sx = self._px - offset_x
        sy = self._py - offset_y
        pygame.draw.rect(screen, NPC_COLOR, (sx, sy, NPC_SIZE, NPC_SIZE))

        if near:
            # [!] indicator above NPC
            font = pygame.font.SysFont("Arial", 18, bold=True)
            indicator = font.render("!", True, INDICATOR_COLOR)
            screen.blit(indicator, (sx + NPC_SIZE // 2 - indicator.get_width() // 2, sy - 22))

    def __repr__(self) -> str:
        return f"Npc({self.id!r}, dialogue={self.dialogue_id!r}, pos=({self._px},{self._py}))"
