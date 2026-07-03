# engine/common/menu_popup.py
#
# Shared centered popup overlay for field menus (spell & status scenes).
# A single-line message with an "ENTER / ESC to dismiss" subline; the
# scene owns the dismiss logic and just calls render_popup() while active.
#
# Thin wrapper over the shared themed toast so these popups match the rest
# of the UI.

from __future__ import annotations

import pygame

from engine.common.ui.chrome import render_toast


POPUP_W = 420
POPUP_H = 88


def render_popup(
    screen: pygame.Surface,
    font_msg: pygame.font.Font,
    font_hint: pygame.font.Font,
    text: str,
) -> None:
    render_toast(
        screen, font_msg, font_hint, text,
        hint="ENTER / ESC to dismiss", width=POPUP_W, height=POPUP_H,
    )
