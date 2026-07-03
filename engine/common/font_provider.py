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
                font = pygame.font.Font(self._font_path, size)
                # The bundled TTF ships in a single weight; honor bold requests
                # with synthetic bold so titles render with the intended
                # emphasis instead of silently dropping the flag.
                font.set_bold(bold)
                self._cache[key] = font
            else:
                self._cache[key] = pygame.font.SysFont(_FALLBACK, size, bold=bold)
        return self._cache[key]

    @property
    def small(self) -> pygame.font.Font:
        return self.get(self._sizes["small"])

    @property
    def medium(self) -> pygame.font.Font:
        return self.get(self._sizes["medium"])

    @property
    def large(self) -> pygame.font.Font:
        return self.get(self._sizes["large"])

    @property
    def xlarge(self) -> pygame.font.Font:
        return self.get(self._sizes["xlarge"])


class FontSet:
    """Declarative lazy font bundle — replaces the hand-rolled
    `_fonts_ready` / `_init_fonts()` boilerplate in every scene.

    Declare once in __init__ (no pygame needed yet):

        self._fonts = FontSet(title=(22, True), row=16, hint=15)

    First attribute access resolves every declared font through the
    global FontProvider (which requires init_fonts / pygame.font init)
    and caches them: `self._fonts.title`, `self._fonts.row`, ...
    """

    def __init__(self, **spec: int | tuple[int, bool]) -> None:
        self._spec = {
            name: (v, False) if isinstance(v, int) else v
            for name, v in spec.items()
        }
        self._resolved: dict[str, pygame.font.Font] | None = None

    def __getattr__(self, name: str) -> pygame.font.Font:
        if name.startswith("_"):
            raise AttributeError(name)
        if self._resolved is None:
            provider = get_fonts()
            self._resolved = {
                n: provider.get(size, bold=bold)
                for n, (size, bold) in self._spec.items()
            }
        try:
            return self._resolved[name]
        except KeyError:
            raise AttributeError(
                f"FontSet has no font {name!r} — declared: {sorted(self._spec)}"
            ) from None


def init_fonts(font_path: str | None, sizes: dict[str, int]) -> FontProvider:
    global _instance
    _instance = FontProvider(font_path, sizes)
    return _instance


def get_fonts() -> FontProvider:
    if _instance is None:
        raise RuntimeError("FontProvider not initialized — call init_fonts() first")
    return _instance
