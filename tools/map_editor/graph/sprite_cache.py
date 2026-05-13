"""Loads single-tile icons from Tiled .tsx sprite sheets for the map editor.

NPCs reference a .tsx character sheet (4-direction × multiple frames); we pull
the first tile, which is conventionally the down-facing standing pose, and
use it as a small icon to overlay on map thumbnails. Item boxes use the
scenario's default object sprite when no per-instance sprite is set.

Loaders return None on failure (missing file, malformed tsx, etc.) — the
caller skips the overlay in that case.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pygame


DEFAULT_ITEM_BOX_SPRITE = "assets/sprites/objects/item_box.tsx"


class SpriteCache:
    def __init__(self, scenario_root: Path) -> None:
        self._scenario_root = scenario_root.resolve()
        self._mem: dict[str, pygame.Surface | None] = {}

    def npc_icon(self, sprite_rel_path: str | None) -> pygame.Surface | None:
        if not sprite_rel_path:
            return None
        return self._load(sprite_rel_path)

    def item_box_icon(self, sprite_rel_path: str | None = None) -> pygame.Surface | None:
        return self._load(sprite_rel_path or DEFAULT_ITEM_BOX_SPRITE)

    def _load(self, rel_path: str) -> pygame.Surface | None:
        if rel_path in self._mem:
            return self._mem[rel_path]
        surf = self._render(rel_path)
        self._mem[rel_path] = surf
        return surf

    def _render(self, rel_path: str) -> pygame.Surface | None:
        full = (self._scenario_root / rel_path).resolve()
        try:
            if full.suffix == ".tsx":
                root = ET.parse(full).getroot()
                tile_w = int(root.get("tilewidth", "32"))
                tile_h = int(root.get("tileheight", "32"))
                image_node = root.find("image")
                if image_node is None:
                    return None
                image_path = (full.parent / image_node.get("source", "")).resolve()
            else:
                image_path = full
                tile_w = tile_h = 0
            sheet = pygame.image.load(str(image_path)).convert_alpha()
            if tile_w <= 0 or tile_h <= 0:
                return sheet
            tile = sheet.subsurface(pygame.Rect(0, 0, tile_w, tile_h)).copy()
            return tile
        except (FileNotFoundError, pygame.error, ET.ParseError):
            return None
