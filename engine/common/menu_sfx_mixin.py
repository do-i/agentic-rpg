# engine/common/menu_sfx_mixin.py
#
# Shared SFX + selection helpers for menu/overlay scenes (inn, item shop,
# apothecary, field menu). Centralizes the hover-beep "selection changed"
# pattern duplicated across many scenes. Subclasses must have a non-None
# `_sfx_manager` attribute — pass `SfxManager.null()` if no audio is wanted.

from __future__ import annotations

import pygame


class MenuSfxMixin:
    """Mix into Scene subclasses with an `_sfx_manager` attribute."""

    _sfx_manager: object

    def _play(self, key: str) -> None:
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
