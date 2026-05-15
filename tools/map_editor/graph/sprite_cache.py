"""Loads single-tile icons from Tiled .tsx sprite sheets for the map editor.

NPCs reference a .tsx character sheet (4-direction × multiple frames); rows
are ordered UP, LEFT, DOWN, RIGHT (see engine.world.sprite_sheet), so the
down-facing idle pose is the first frame of row 2. We pull that tile when the
sheet has the rows for it, otherwise fall back to the first tile. Item boxes
use the scenario's default object sprite when no per-instance sprite is set.

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
            # Row 2 is the down-facing pose on character sheets; fall back to
            # row 0 for short sheets (e.g. the 1-row item-box tileset).
            down_row = 2
            row_y = down_row * tile_h if (down_row + 1) * tile_h <= sheet.get_height() else 0
            tile = sheet.subsurface(pygame.Rect(0, row_y, tile_w, tile_h)).copy()
            return tile
        except (FileNotFoundError, pygame.error, ET.ParseError):
            return None
