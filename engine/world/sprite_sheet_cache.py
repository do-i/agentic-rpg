# engine/world/sprite_sheet_cache.py
#
# Process-wide cache of SpriteSheet instances, keyed by absolute Path.
# Promoted from a per-EnemySpawner dict (§2.8) so sheets survive map
# transitions instead of being re-read from disk every time the spawner
# is rebuilt or NpcLoader.parse_from_map_data is called.
#
# A None sheet is also cached: for missing/corrupt files we don't want
# to re-stat the path and re-attempt the parse on every call.

from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pygame

from engine.world.sprite_sheet import SpriteSheet

_log = logging.getLogger(__name__)


class SpriteSheetCache:
    """Lazy SpriteSheet cache. `get(path)` returns the cached sheet, loading
    on first call. Missing/corrupt sheets are cached as None so the failure
    is logged once."""

    def __init__(self) -> None:
        self._cache: dict[Path, SpriteSheet | None] = {}

    def get(self, path: Path) -> SpriteSheet | None:
        if path in self._cache:
            return self._cache[path]
        if not path.exists():
            self._cache[path] = None
            return None
        try:
            sheet: SpriteSheet | None = SpriteSheet(path)
        except (pygame.error, OSError, ParseError, KeyError, ValueError) as e:
            _log.warning("Sprite sheet load failed: %s — %s", path, e)
            sheet = None
        self._cache[path] = sheet
        return sheet

    def clear(self) -> None:
        self._cache.clear()
