# engine/common/menu_row_renderer.py
#
# Shared row renderer for list/picker menus (equip, spell, ...).
# Draws a single text row with optional focus highlight or dimmed-selection
# indicator (used when the row is selected on a non-active page).

from __future__ import annotations

import pygame

from engine.common.color_constants import C_SEL, C_ROW_SEL


C_DIMMED_BG  = (26, 26, 46)
C_DIMMED_BDR = (60, 60, 80)


def render_row(
    screen: pygame.Surface,
    font: pygame.font.Font,
    x: int,
    y: int,
    w: int,
    text: str,
    focused: bool,
    dimmed_sel: bool,
    text_color: tuple[int, int, int],
) -> None:
    row_h = font.get_height() + 10
    if focused:
        pygame.draw.rect(screen, C_ROW_SEL, (x - 4, y - 2, w, row_h))
        pygame.draw.rect(screen, C_SEL,     (x - 4, y - 2, w, row_h), 2)
    elif dimmed_sel:
        pygame.draw.rect(screen, C_DIMMED_BG,  (x - 4, y - 2, w, row_h))
        pygame.draw.rect(screen, C_DIMMED_BDR, (x - 4, y - 2, w, row_h), 1)
    screen.blit(font.render(text, True, text_color), (x, y))
