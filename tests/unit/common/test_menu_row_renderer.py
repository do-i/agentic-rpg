# tests/unit/core/state/test_menu_row_renderer.py
#
# Smoke tests for the shared MenuRowRenderer helper. The renderer is pure
# pygame drawing so we assert pixel sampling at a few known offsets.

from __future__ import annotations

import pytest
import pygame

from engine.common.menu_row_renderer import (
    render_row, C_DIMMED_BG, C_DIMMED_BDR,
)
from engine.common.color_constants import C_SEL, C_ROW_SEL, C_TEXT


@pytest.fixture
def screen():
    pygame.init()
    surf = pygame.Surface((200, 80))
    yield surf
    pygame.quit()


@pytest.fixture
def font():
    pygame.init()
    return pygame.font.SysFont(None, 16)


def test_focused_row_paints_selection_fill(screen, font):
    screen.fill((0, 0, 0))
    render_row(screen, font, 20, 20, 100, "x", focused=True, dimmed_sel=False, text_color=C_TEXT)
    # The fill rect starts at (x-4, y-2) and is C_ROW_SEL inside the border.
    # Sample one pixel inside the fill, away from the 2px border and the glyph.
    assert screen.get_at((100, 30))[:3] == C_ROW_SEL


def test_focused_row_paints_selection_border(screen, font):
    screen.fill((0, 0, 0))
    render_row(screen, font, 20, 20, 100, "x", focused=True, dimmed_sel=False, text_color=C_TEXT)
    # The 2px border sits on the outer edge of the rect (x-4, y-2).
    assert screen.get_at((20 - 4, 20 - 2))[:3] == C_SEL


def test_dimmed_sel_row_uses_dimmed_palette(screen, font):
    screen.fill((0, 0, 0))
    render_row(screen, font, 20, 20, 100, "x", focused=False, dimmed_sel=True, text_color=C_TEXT)
    assert screen.get_at((100, 30))[:3] == C_DIMMED_BG
    assert screen.get_at((20 - 4, 20 - 2))[:3] == C_DIMMED_BDR


def test_unfocused_undimmed_row_paints_only_text(screen, font):
    screen.fill((0, 0, 0))
    render_row(screen, font, 20, 20, 100, "x", focused=False, dimmed_sel=False, text_color=C_TEXT)
    # No background fill — sample inside what would have been the rect.
    assert screen.get_at((100, 30))[:3] == (0, 0, 0)


def test_focused_takes_precedence_over_dimmed(screen, font):
    screen.fill((0, 0, 0))
    render_row(screen, font, 20, 20, 100, "x", focused=True, dimmed_sel=True, text_color=C_TEXT)
    # focused branch wins; we should see C_ROW_SEL not C_DIMMED_BG.
    assert screen.get_at((100, 30))[:3] == C_ROW_SEL
