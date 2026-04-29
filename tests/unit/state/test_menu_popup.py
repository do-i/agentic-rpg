# tests/unit/core/state/test_menu_popup.py
#
# Smoke tests for the shared MenuPopup helper.

import pytest
import pygame

from engine.common.menu_popup import (
    render_popup, POPUP_W, POPUP_H, C_POPUP_BG, C_POPUP_BORDER,
)


@pytest.fixture
def screen():
    pygame.init()
    surf = pygame.Surface((640, 480))
    yield surf
    pygame.quit()


@pytest.fixture
def font():
    pygame.init()
    return pygame.font.SysFont(None, 16)


def test_popup_centered_with_background_and_border(screen, font):
    screen.fill((0, 0, 0))
    render_popup(screen, font, font, "hello")
    sw, sh = screen.get_size()
    # Centered upper-left corner of the popup rect.
    x = (sw - POPUP_W) // 2
    y = (sh - POPUP_H) // 2
    # Border pixel
    assert screen.get_at((x, y))[:3] == C_POPUP_BORDER
    # Interior pixel — well inside the rect, away from text
    assert screen.get_at((x + 5, y + POPUP_H - 5))[:3] == C_POPUP_BG


def test_popup_renders_message_text(screen, font):
    screen.fill((0, 0, 0))
    render_popup(screen, font, font, "test message")
    # If text rendered, *some* pixel in the row centered ~y+20 must be
    # neither background nor border (i.e. the text glyph).
    sw, sh = screen.get_size()
    x = (sw - POPUP_W) // 2
    y = (sh - POPUP_H) // 2
    text_row_y = y + 28
    found_glyph = False
    for px in range(x + 10, x + POPUP_W - 10):
        c = screen.get_at((px, text_row_y))[:3]
        if c not in (C_POPUP_BG, C_POPUP_BORDER, (0, 0, 0)):
            found_glyph = True
            break
    assert found_glyph
