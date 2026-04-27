# engine/common/menu_popup.py
#
# Shared centered popup overlay for field menus (spell scene today).
# A single-line message with an "ENTER / ESC to dismiss" subline; the
# scene owns the dismiss logic and just calls render_popup() while active.

from __future__ import annotations

import pygame

from engine.common.color_constants import C_TEXT, C_TEXT_DIM


POPUP_W = 420
POPUP_H = 80
C_POPUP_BG     = (30, 30, 52)
C_POPUP_BORDER = (140, 140, 200)


def render_popup(
    screen: pygame.Surface,
    font_msg: pygame.font.Font,
    font_hint: pygame.font.Font,
    text: str,
) -> None:
    sw, sh = screen.get_size()
    x = (sw - POPUP_W) // 2
    y = (sh - POPUP_H) // 2
    pygame.draw.rect(screen, C_POPUP_BG,     (x, y, POPUP_W, POPUP_H))
    pygame.draw.rect(screen, C_POPUP_BORDER, (x, y, POPUP_W, POPUP_H), 2)
    msg = font_msg.render(text, True, C_TEXT)
    screen.blit(msg, (x + (POPUP_W - msg.get_width()) // 2, y + 20))
    sub = font_hint.render("ENTER / ESC to dismiss", True, C_TEXT_DIM)
    screen.blit(sub, (x + (POPUP_W - sub.get_width()) // 2, y + POPUP_H - 24))
