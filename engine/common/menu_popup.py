# engine/common/menu_popup.py
#
# Shared centered popup overlay for field menus (spell & status scenes).
# A single-line message with an "ENTER / ESC to dismiss" subline; the
# scene owns the dismiss logic and just calls render_popup() while active.
#
# Uses the shared themed modal so these popups match the rest of the UI.

from __future__ import annotations

import pygame

from engine.common.field_menu_theme import DIM, INK, render_modal


POPUP_W = 420
POPUP_H = 88


def render_popup(
    screen: pygame.Surface,
    font_msg: pygame.font.Font,
    font_hint: pygame.font.Font,
    text: str,
) -> None:
    modal = render_modal(screen, POPUP_W, POPUP_H)
    msg = font_msg.render(text, True, INK)
    screen.blit(msg, (modal.x + (POPUP_W - msg.get_width()) // 2, modal.y + 20))
    sub = font_hint.render("ENTER / ESC to dismiss", True, DIM)
    screen.blit(sub, (modal.x + (POPUP_W - sub.get_width()) // 2, modal.bottom - 28))
