# engine/world/sprite_sheet.py

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError

import pygame


class Direction(IntEnum):
    UP    = 0
    LEFT  = 1
    DOWN  = 2
    RIGHT = 3


# TSX row order matches Direction enum values
# row 0 = UP, row 1 = LEFT, row 2 = DOWN, row 3 = RIGHT
FRAME_WIDTH  = 64
FRAME_HEIGHT = 64
FRAMES_PER_ROW = 9


class SpriteSheet:
    """
    Loads a TSX file, reads the referenced image, slices into frames.
    Frames indexed by (direction, frame_index).

    TSX layout assumption:
        row 0 — UP    (frames 1 - 8)
        row 1 — LEFT  (frames 10 - 17)
        row 2 — DOWN  (frames 19 - 26)
        row 3 — RIGHT (frames 28 - 35)
    """

    def __init__(self, tsx_path: str | Path) -> None:
        self._tsx_path = Path(tsx_path)
        self._frames: dict[tuple[Direction, int], pygame.Surface] = {}
        self._load()

    def _load(self) -> None:
        tree = ElementTree.parse(self._tsx_path)
        root = tree.getroot()

        image_el = root.find("image")
        if image_el is None:
            raise ValueError(f"No <image> element found in {self._tsx_path}")

        image_src = image_el.attrib["source"]
        image_path = (self._tsx_path.parent / image_src).resolve()
        # sheet = pygame.image.load(str(image_path)).convert_alpha()
        sheet = pygame.image.load(str(image_path))

        for direction in Direction:
            row = direction.value
            for col in range(FRAMES_PER_ROW):
                x = col * FRAME_WIDTH
                y = row * FRAME_HEIGHT
                frame = sheet.subsurface(pygame.Rect(x, y, FRAME_WIDTH, FRAME_HEIGHT))
                self._frames[(direction, col)] = frame

    def get_portrait(self, direction: Direction = Direction.DOWN) -> pygame.Surface:
        """Return the head region of the idle frame, suitable for dialogue portraits."""
        idle = self.get_frame(direction, 0)
        # Top 50 % of the 64 px frame captures the head/shoulders.
        crop_h = int(FRAME_HEIGHT * 0.5)
        crop_w = int(FRAME_WIDTH * 0.5)
        head = idle.subsurface(pygame.Rect(16, 10, crop_w, crop_h))
        return head

    def get_frame(self, direction: Direction, frame_index: int) -> pygame.Surface:
        """Returns the surface for the given direction and frame index."""
        key = (direction, frame_index % FRAMES_PER_ROW)
        return self._frames[key]

    @property
    def frame_count(self) -> int:
        return FRAMES_PER_ROW

    def __repr__(self) -> str:
        return f"SpriteSheet({self._tsx_path.name}, frames={len(self._frames)})"

    @staticmethod
    def load_npc_face(path: Path | str, size: int) -> pygame.Surface | None:
        """Load an NPC's idle DOWN frame and scale to (size, size).

        Returns None if the sheet/image fails to load — callers fall back
        to a placeholder. Used by inn/shop/apothecary overlays for the
        small NPC portrait beside their title.
        """
        if path is None:
            return None
        try:
            sheet = SpriteSheet(path)
            frame = sheet.get_frame(Direction.DOWN, 0)
            return pygame.transform.scale(frame, (size, size))
        except (FileNotFoundError, OSError, pygame.error, ValueError, KeyError, ParseError):
            return None
