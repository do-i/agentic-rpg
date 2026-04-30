# tests/unit/core/common/test_menu_sfx_mixin.py

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from engine.audio.sfx_manager import SfxManager
from engine.common.menu_sfx_mixin import MenuSfxMixin


class _Host(MenuSfxMixin):
    def __init__(self, sfx) -> None:
        self._sfx_manager = sfx


class TestPlay:
    def test_calls_play_when_sfx_present(self):
        sfx = MagicMock()
        host = _Host(sfx)
        host._play("hover")
        sfx.play.assert_called_once_with("hover")

    def test_no_op_when_null_sfx(self):
        # No exception raised — null SfxManager swallows the call.
        _Host(SfxManager.null())._play("hover")


class TestSetSelHover:
    def test_returns_new_value(self):
        host = _Host(MagicMock())
        assert host._set_sel_hover(0, 3) == 3

    def test_plays_hover_when_changed(self):
        sfx = MagicMock()
        host = _Host(sfx)
        host._set_sel_hover(2, 5)
        sfx.play.assert_called_once_with("hover")

    def test_silent_when_unchanged(self):
        sfx = MagicMock()
        host = _Host(sfx)
        result = host._set_sel_hover(2, 2)
        sfx.play.assert_not_called()
        assert result == 2

    def test_null_sfx_manager_still_returns_new(self):
        assert _Host(SfxManager.null())._set_sel_hover(0, 7) == 7


class TestIsPopupDismissKey:
    @pytest.mark.parametrize("key", [
        pygame.K_ESCAPE,
        pygame.K_RETURN,
        pygame.K_KP_ENTER,
    ])
    def test_dismiss_keys(self, key):
        assert MenuSfxMixin.is_popup_dismiss_key(key) is True

    @pytest.mark.parametrize("key", [
        pygame.K_a,
        pygame.K_UP,
        pygame.K_DOWN,
        pygame.K_SPACE,
    ])
    def test_other_keys(self, key):
        assert MenuSfxMixin.is_popup_dismiss_key(key) is False
