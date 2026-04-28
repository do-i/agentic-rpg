# engine/common/menu_sfx_mixin.py
#
# Shared SFX + selection helpers for menu/overlay scenes (inn, item shop,
# apothecary, field menu). Centralizes the `if self._sfx_manager: play(...)`
# guard and the hover-beep "selection changed" pattern that was duplicated
# across ~80 sites. Subclasses just need a `_sfx_manager` attribute (which
# may be None — every helper here is a no-op when it is).

from __future__ import annotations

import pygame


class MenuSfxMixin:
    """Mix into Scene subclasses with an `_sfx_manager` attribute."""

    _sfx_manager: object | None

    def _play(self, key: str) -> None:
        if self._sfx_manager:
            self._sfx_manager.play(key)

    def _set_sel_hover(self, current: int, new: int) -> int:
        """Return `new`, playing the hover beep when it differs from `current`.

        Convenience for the UP/DOWN navigation pattern that every scene
        repeats: clamp/wrap the new index, play `hover` on change, write
        it back.
        """
        if new != current:
            self._play("hover")
        return new

    @staticmethod
    def is_popup_dismiss_key(key: int) -> bool:
        """ENTER / RETURN / ESC all dismiss a single-line popup."""
        return key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER)
