# engine/shop/shop_scene_mixin.py
#
# Shared sub-state key handling for the shop overlay family (item shop,
# apothecary, magic-core shop). Each scene keeps its own state machine;
# the recurring shapes — popup dismissal, UP/DOWN list navigation with
# hover SFX, ESC-to-close — live here.

from __future__ import annotations

import pygame

from engine.common.menu_sfx_mixin import MenuSfxMixin
from engine.shop.shop_constants import STATE_LIST


class ShopSceneMixin(MenuSfxMixin):
    """Mix into shop overlay scenes with `_state`, `_list` (ScrollListState),
    `_on_close`, and `_sfx_manager` attributes."""

    def _handle_popup(self, key: int) -> None:
        if self.is_popup_dismiss_key(key):
            self._after_popup_dismiss()

    def _after_popup_dismiss(self) -> None:
        """Where a dismissed popup lands. Default: back to the list."""
        self._state = STATE_LIST

    def _nav_list(self, key: int, count: int) -> bool:
        """UP/DOWN cursor movement with hover SFX on change.
        Returns True when the key was consumed."""
        if key == pygame.K_UP:
            if self._list.move(-1, count):
                self._play("hover")
            return True
        if key == pygame.K_DOWN:
            if self._list.move(1, count):
                self._play("hover")
            return True
        return False

    def _close_shop(self) -> None:
        self._play("cancel")
        self._on_close()
