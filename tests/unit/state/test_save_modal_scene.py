from __future__ import annotations

from unittest.mock import MagicMock

import pygame

from engine.common.field_menu_theme import dim_screen
from engine.title.save_modal_scene import SaveModalScene


def _scene() -> SaveModalScene:
    return SaveModalScene(
        game_state_manager=MagicMock(),
        state=MagicMock(),
        on_close=MagicMock(),
        sfx_manager=MagicMock(),
    )


def test_scene_constructs():
    # The modal now leans on the shared field-menu theme for its chrome;
    # this guards that construction (slot loading) still works.
    assert _scene() is not None


def test_dim_screen_darkens_background():
    pygame.init()
    try:
        screen = pygame.Surface((640, 480))
        screen.fill((255, 255, 255))
        dim_screen(screen)
        # Top-left pixel should be darkened toward the veil color.
        r, g, b = screen.get_at((0, 0))[:3]
        assert (r, g, b) != (255, 255, 255)
        assert max(r, g, b) < 255
    finally:
        pygame.quit()
