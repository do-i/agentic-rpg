# tests/unit/core/state/test_menu_popup.py
#
# Smoke tests for the shared MenuPopup helper. The popup now uses the shared
# themed modal, so we assert structural behaviour (a panel is drawn and the
# message renders) rather than exact flat-fill colors.

from __future__ import annotations

import pytest
import pygame

from engine.common.menu_popup import render_popup, POPUP_W, POPUP_H


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


def test_popup_draws_themed_panel(screen, font):
    screen.fill((0, 0, 0))
    render_popup(screen, font, font, "hello")
    sw, sh = screen.get_size()
    # Center of the popup rect should be painted by the themed panel,
    # i.e. no longer pure black.
    cx, cy = sw // 2, sh // 2
    assert screen.get_at((cx, cy))[:3] != (0, 0, 0)


def test_popup_renders_message_text(screen, font):
    screen.fill((0, 0, 0))
    render_popup(screen, font, font, "test message")
    sw, sh = screen.get_size()
    x = (sw - POPUP_W) // 2
    y = (sh - POPUP_H) // 2
    # A glyph from the message must appear on the upper text row.
    text_row_y = y + 28
    panel_bg = screen.get_at((x + 5, y + POPUP_H - 5))[:3]
    found_glyph = any(
        screen.get_at((px, text_row_y))[:3] not in (panel_bg, (0, 0, 0))
        for px in range(x + 10, x + POPUP_W - 10)
    )
    assert found_glyph
