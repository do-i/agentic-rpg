from __future__ import annotations

from unittest.mock import MagicMock

import pygame

from engine.title.save_modal_scene import SaveModalScene


def _scene() -> SaveModalScene:
    return SaveModalScene(
        game_state_manager=MagicMock(),
        state=MagicMock(),
        on_close=MagicMock(),
        sfx_manager=MagicMock(),
    )


def test_dim_overlay_is_reused_for_same_screen_size():
    pygame.init()
    try:
        scene = _scene()
        screen = pygame.Surface((640, 480))

        first = scene._get_dim_overlay(screen)
        second = scene._get_dim_overlay(screen)

        assert first is second
    finally:
        pygame.quit()


def test_dim_overlay_is_rebuilt_when_screen_size_changes():
    pygame.init()
    try:
        scene = _scene()

        first = scene._get_dim_overlay(pygame.Surface((640, 480)))
        second = scene._get_dim_overlay(pygame.Surface((800, 600)))

        assert first is not second
        assert second.get_size() == (800, 600)
    finally:
        pygame.quit()
