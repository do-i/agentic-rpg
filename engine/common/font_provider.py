# engine/common/font_provider.py

from __future__ import annotations

import pygame

_FALLBACK = "monospace"
_instance: "FontProvider | None" = None


class FontProvider:
    """
    Loads a TTF font (or system fallback) and vends pygame.font.Font instances
    by pixel size with an LRU-style cache.  Named aliases map to the four sizes
    configured in settings.yaml under fonts.sizes.
    """

    def __init__(self, font_path: str | None, sizes: dict[str, int]) -> None:
        self._font_path = font_path
        self._sizes = sizes
        self._cache: dict[tuple[int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._cache:
            if self._font_path:
                self._cache[key] = pygame.font.Font(self._font_path, size)
            else:
                self._cache[key] = pygame.font.SysFont(_FALLBACK, size, bold=bold)
        return self._cache[key]

    @property
    def small(self) -> pygame.font.Font:
        return self.get(self._sizes.get("small", 14))

    @property
    def medium(self) -> pygame.font.Font:
        return self.get(self._sizes.get("medium", 18))

    @property
    def large(self) -> pygame.font.Font:
        return self.get(self._sizes.get("large", 22))

    @property
    def xlarge(self) -> pygame.font.Font:
        return self.get(self._sizes.get("xlarge", 28))


def init_fonts(font_path: str | None, sizes: dict[str, int]) -> FontProvider:
    global _instance
    _instance = FontProvider(font_path, sizes)
    return _instance


def get_fonts() -> FontProvider:
    if _instance is None:
        raise RuntimeError("FontProvider not initialized — call init_fonts() first")
    return _instance
