# engine/world/item_box_sprite.py

from pathlib import Path
from xml.etree import ElementTree

import pygame


class ItemBoxSprite:
    """
    Minimal 2-frame horizontal sheet loader for item boxes.
    TSX layout: [closed | opened], each frame tilewidth × tileheight.
    """

    def __init__(self, tsx_path: str | Path) -> None:
        self._tsx_path = Path(tsx_path)
        self._closed: pygame.Surface
        self._opened: pygame.Surface
        self._load()

    def _load(self) -> None:
        tree = ElementTree.parse(self._tsx_path)
        root = tree.getroot()

        tile_w = int(root.attrib["tilewidth"])
        tile_h = int(root.attrib["tileheight"])

        image_el = root.find("image")
        if image_el is None:
            raise ValueError(f"No <image> element found in {self._tsx_path}")
        image_src = image_el.attrib["source"]
        image_path = (self._tsx_path.parent / image_src).resolve()

        sheet = pygame.image.load(str(image_path))
        self._closed = sheet.subsurface(pygame.Rect(0, 0, tile_w, tile_h))
        self._opened = sheet.subsurface(pygame.Rect(tile_w, 0, tile_w, tile_h))
        self._width = tile_w
        self._height = tile_h

    def closed(self) -> pygame.Surface:
        return self._closed

    def opened(self) -> pygame.Surface:
        return self._opened

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def __repr__(self) -> str:
        return f"ItemBoxSprite({self._tsx_path.name})"
