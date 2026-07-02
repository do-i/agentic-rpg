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
    Frame geometry (tile size, columns) comes from the TSX attributes,
    so 64 px map sheets and larger pre-rendered battle sheets share one
    loader. Frames indexed by (row, frame_index). Callers fetch via
    get_frame with a Direction and an optional row_offset for sheets
    where the walk cycle is not in rows 0-3 (e.g. LPC 12-row enemy
    sheets place walk in rows 8-11).
    """

    def __init__(self, tsx_path: str | Path) -> None:
        self._tsx_path = Path(tsx_path)
        self._frames: dict[tuple[int, int], pygame.Surface] = {}
        self._scaled_frames: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._row_count: int = 0
        self._frame_w: int = FRAME_WIDTH
        self._frame_h: int = FRAME_HEIGHT
        self._columns: int = FRAMES_PER_ROW
        self._load()

    def _tileset_attr(self, root, name: str) -> int:
        value = root.attrib.get(name)
        if value is None:
            raise ValueError(
                f'Missing "{name}" attribute on <tileset> in {self._tsx_path} '
                f'— e.g. <tileset ... {name}="64">'
            )
        return int(value)

    def _load(self) -> None:
        tree = ElementTree.parse(self._tsx_path)
        root = tree.getroot()

        image_el = root.find("image")
        if image_el is None:
            raise ValueError(f"No <image> element found in {self._tsx_path}")

        self._frame_w = self._tileset_attr(root, "tilewidth")
        self._frame_h = self._tileset_attr(root, "tileheight")
        self._columns = self._tileset_attr(root, "columns")

        image_src = image_el.attrib["source"]
        image_path = (self._tsx_path.parent / image_src).resolve()
        sheet = pygame.image.load(str(image_path))

        self._row_count = sheet.get_height() // self._frame_h
        for row in range(self._row_count):
            for col in range(self._columns):
                x = col * self._frame_w
                y = row * self._frame_h
                frame = sheet.subsurface(pygame.Rect(x, y, self._frame_w, self._frame_h))
                self._frames[(row, col)] = frame

    def get_portrait(self, direction: Direction = Direction.DOWN) -> pygame.Surface:
        """Return the head region of the idle frame, suitable for dialogue portraits."""
        idle = self.get_frame(direction, 0)
        # Top 50 % of the frame captures the head/shoulders.
        crop_w = int(self._frame_w * 0.5)
        crop_h = int(self._frame_h * 0.5)
        x = self._frame_w // 4
        y = int(self._frame_h * 10 / 64)
        head = idle.subsurface(pygame.Rect(x, y, crop_w, crop_h))
        return head

    def get_frame(
        self, direction: Direction, frame_index: int, row_offset: int = 0
    ) -> pygame.Surface:
        """Returns the surface for the given direction and frame index.
        row_offset shifts the row used (e.g. LPC 12-row sheets put the
        walk cycle at rows 8-11, so callers pass row_offset=8).
        """
        key = (direction.value + row_offset, frame_index % self._columns)
        return self._frames[key]

    def get_scaled_frame(
        self,
        direction: Direction,
        frame_index: int,
        size: tuple[int, int],
        row_offset: int = 0,
    ) -> pygame.Surface:
        row = direction.value + row_offset
        col = frame_index % self._columns
        key = (row, col, size[0], size[1])
        if key not in self._scaled_frames:
            self._scaled_frames[key] = pygame.transform.scale(
                self._frames[(row, col)], size
            )
        return self._scaled_frames[key]

    @property
    def frame_count(self) -> int:
        return self._columns

    @property
    def frame_size(self) -> tuple[int, int]:
        return (self._frame_w, self._frame_h)

    @property
    def row_count(self) -> int:
        return self._row_count

    @property
    def tsx_path(self) -> Path:
        return self._tsx_path

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
