# engine/shop/shop_renderer.py
#
# Shared rendering helpers used by all shop scenes.

from __future__ import annotations

import pygame

from engine.common.field_menu_theme import (
    dim_screen,
    draw_divider,
    render_panel,
    render_toast,
)
from engine.shop.shop_constants import (
    C_HINT,
    HEADER_H,
)


def draw_dim_overlay(screen: pygame.Surface) -> None:
    dim_screen(screen)


def draw_modal_box(
    screen: pygame.Surface,
    mx: int,
    my: int,
    mw: int,
    mh: int,
    border_color: tuple[int, int, int],
    border_width: int = 2,
) -> None:
    # border_color / border_width retained for call-site compatibility; the
    # themed panel supplies its own border.
    render_panel(screen, pygame.Rect(mx, my, mw, mh), active=True)


def draw_shop_header(
    screen: pygame.Surface,
    mx: int,
    my: int,
    mw: int,
    title_text: str,
    title_color: tuple[int, int, int],
    gp: int,
    gp_color: tuple[int, int, int],
    font_title: pygame.font.Font,
    font_row: pygame.font.Font,
    pad: int,
    sprite_surf: pygame.Surface | None = None,
    sprite_size: int = 0,
) -> None:
    text_x = mx + pad
    if sprite_surf:
        screen.blit(sprite_surf, (mx + pad, my + (HEADER_H - sprite_size) // 2))
        text_x = mx + pad + sprite_size + 12

    title = font_title.render(title_text, True, title_color)
    screen.blit(title, (text_x, my + (HEADER_H - title.get_height()) // 2))

    gp_s = font_row.render(f"GP  {gp:,}", True, gp_color)
    screen.blit(
        gp_s, (mx + mw - gp_s.get_width() - pad, my + (HEADER_H - gp_s.get_height()) // 2)
    )

    draw_divider(screen, mx + 10, my + HEADER_H, mw - 20)


def draw_footer(
    screen: pygame.Surface,
    mx: int,
    y: int,
    mw: int,
    pad: int,
    hint_text: str,
    font_hint: pygame.font.Font,
) -> None:
    draw_divider(screen, mx + 10, y, mw - 20)
    hint = font_hint.render(hint_text, True, C_HINT)
    screen.blit(hint, (mx + pad, y + 8))


def draw_popup(
    screen: pygame.Surface,
    popup_w: int,
    message: str,
    msg_color: tuple[int, int, int],
    border_color: tuple[int, int, int],
    font_toast: pygame.font.Font,
    font_hint: pygame.font.Font,
) -> None:
    # border_color retained for call-site compatibility; the themed toast
    # supplies its own border.
    render_toast(
        screen, font_toast, font_hint, message,
        msg_color=msg_color, width=popup_w,
    )


