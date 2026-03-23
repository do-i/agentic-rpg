# engine/world/sprite_sheet.py

from enum import IntEnum
from pathlib import Path
from xml.etree import ElementTree

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
FRAMES_PER_ROW = 8


class SpriteSheet:
    """
    Loads a TSX file, reads the referenced image, slices into frames.
    Frames indexed by (direction, frame_index).

    TSX layout assumption:
        row 0 — UP    (frames 0 - 7)
        row 1 — LEFT  (frames 8 - 15)
        row 2 — DOWN  (frames 16 - 23)
        row 3 — RIGHT (frames 24 - 31)
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

    def get_frame(self, direction: Direction, frame_index: int) -> pygame.Surface:
        """Returns the surface for the given direction and frame index."""
        key = (direction, frame_index % FRAMES_PER_ROW)
        return self._frames[key]

    @property
    def frame_count(self) -> int:
        return FRAMES_PER_ROW

    def __repr__(self) -> str:
        return f"SpriteSheet({self._tsx_path.name}, frames={len(self._frames)})"
