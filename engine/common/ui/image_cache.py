# engine/common/ui/image_cache.py
#
# Display-keyed image loading and caching. Caches are keyed by the live
# display surface id so they invalidate naturally across display re-inits
# (and are bypassed entirely when no display exists, e.g. in unit tests).

from __future__ import annotations

from pathlib import Path

import pygame

_IMAGE_CACHE: dict[tuple[int, Path], pygame.Surface | None] = {}


def display_cache_id() -> int:
    display = pygame.display.get_surface() if pygame.display.get_init() else None
    return id(display) if display is not None else 0


def load_image(path: Path) -> pygame.Surface | None:
    display_id = display_cache_id()
    if display_id == 0:
        return _load_image_uncached(path)
    cache_key = (display_id, path)
    if cache_key not in _IMAGE_CACHE:
        _IMAGE_CACHE[cache_key] = _load_image_uncached(path)
    return _IMAGE_CACHE[cache_key]


def _load_image_uncached(path: Path) -> pygame.Surface | None:
    try:
        image = pygame.image.load(str(path))
        if pygame.display.get_surface() is not None:
            return image.convert_alpha()
        return image
    except (FileNotFoundError, pygame.error):
        return None
