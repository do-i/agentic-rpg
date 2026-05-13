"""On-demand thumbnail rendering for graph nodes.

Each TMX is rendered to a small surface and cached to disk under the
scenario root (so the cache is portable, and ignorable in .gitignore).
The cache key is (tmx mtime, thumbnail size); a stale cache simply
re-renders.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from engine.world.tile_map import TileMap


THUMB_MAX_W = 256
THUMB_MAX_H = 192
CACHE_DIRNAME = ".cache/map_editor/thumbs"


class ThumbnailCache:
    def __init__(self, scenario_root: Path) -> None:
        self._cache_dir = (scenario_root / CACHE_DIRNAME).resolve()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._thumb_memory: dict[Path, pygame.Surface] = {}
        self._full_memory: dict[Path, pygame.Surface] = {}

    def get(self, tmx_path: Path) -> pygame.Surface | None:
        """Return the small thumbnail (bounded by THUMB_MAX_W/H), cached to disk."""
        if tmx_path in self._thumb_memory:
            return self._thumb_memory[tmx_path]

        disk_path = self._disk_path(tmx_path)
        if disk_path.is_file() and disk_path.stat().st_mtime >= tmx_path.stat().st_mtime:
            try:
                surf = pygame.image.load(str(disk_path)).convert_alpha()
                self._thumb_memory[tmx_path] = surf
                return surf
            except pygame.error:
                pass

        full = self.get_full(tmx_path)
        if full is None:
            return None
        scale = min(THUMB_MAX_W / full.get_width(), THUMB_MAX_H / full.get_height(), 1.0)
        if scale < 1.0:
            new_size = (
                max(1, int(full.get_width() * scale)),
                max(1, int(full.get_height() * scale)),
            )
            thumb = pygame.transform.smoothscale(full, new_size)
        else:
            thumb = full.copy()
        pygame.image.save(thumb, str(disk_path))
        self._thumb_memory[tmx_path] = thumb
        return thumb

    def get_full(self, tmx_path: Path) -> pygame.Surface | None:
        """Return the map rendered at its native pixel size (cached in memory only)."""
        if tmx_path in self._full_memory:
            return self._full_memory[tmx_path]
        try:
            tile_map = TileMap(str(tmx_path))
        except Exception:
            return None
        full = pygame.Surface(
            (tile_map.width_px, tile_map.height_px), pygame.SRCALPHA
        )
        tile_map.render(full, 0, 0)
        self._full_memory[tmx_path] = full
        return full

    def _disk_path(self, tmx_path: Path) -> Path:
        return self._cache_dir / f"{tmx_path.stem}.png"
