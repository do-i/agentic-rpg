# engine/shop/shop_renderer.py
#
# Shared rendering helpers used by all shop scenes.

from __future__ import annotations

import pygame

from engine.shop.shop_constants import (
    C_BG,
    C_DIVIDER,
    C_HINT,
    C_NORM_BDR,
    C_ROW_BG,
    HEADER_H,
    MODAL_W,
)


def draw_dim_overlay(screen: pygame.Surface) -> None:
    overlay = pygame.Surface(
        (screen.get_width(), screen.get_height()), pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))


def draw_modal_box(
    screen: pygame.Surface,
    mx: int,
    my: int,
    mw: int,
    mh: int,
    border_color: tuple[int, int, int],
    border_width: int = 2,
) -> None:
    pygame.draw.rect(screen, C_BG, (mx, my, mw, mh), border_radius=8)
    pygame.draw.rect(
        screen, border_color, (mx, my, mw, mh), border_width, border_radius=8
    )


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

    pygame.draw.line(
        screen, C_DIVIDER, (mx + 10, my + HEADER_H), (mx + mw - 10, my + HEADER_H)
    )


def draw_list_row_box(
    screen: pygame.Surface,
    rx: int,
    row_y: int,
    rw: int,
    row_h: int,
    selected: bool,
    sel_bg: tuple[int, int, int],
    sel_bdr: tuple[int, int, int],
) -> None:
    bg = sel_bg if selected else C_ROW_BG
    bdr = sel_bdr if selected else C_NORM_BDR
    pygame.draw.rect(screen, bg, (rx, row_y, rw, row_h), border_radius=4)
    pygame.draw.rect(screen, bdr, (rx, row_y, rw, row_h), 1, border_radius=4)


def draw_cursor_arrow(
    screen: pygame.Surface,
    rx: int,
    row_y: int,
    row_h: int,
    color: tuple[int, int, int],
    font: pygame.font.Font,
) -> None:
    cur = font.render(" ", True, color)
    screen.blit(cur, (rx + 8, row_y + (row_h - cur.get_height()) // 2))


def draw_footer(
    screen: pygame.Surface,
    mx: int,
    y: int,
    mw: int,
    pad: int,
    hint_text: str,
    font_hint: pygame.font.Font,
) -> None:
    pygame.draw.line(screen, C_DIVIDER, (mx + 10, y), (mx + mw - 10, y))
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
    ph = 80
    px = (screen.get_width() - popup_w) // 2
    py = (screen.get_height() - ph) // 2
    pygame.draw.rect(screen, C_BG, (px, py, popup_w, ph), border_radius=6)
    pygame.draw.rect(screen, border_color, (px, py, popup_w, ph), 2, border_radius=6)
    msg = font_toast.render(message, True, msg_color)
    screen.blit(msg, (px + (popup_w - msg.get_width()) // 2, py + 14))
    hint = font_hint.render("ENTER / ESC  close", True, C_HINT)
    screen.blit(hint, (px + (popup_w - hint.get_width()) // 2, py + ph - 28))


def draw_scroll_hints(
    screen: pygame.Surface,
    mx: int,
    y: int,
    mw: int,
    scroll: int,
    total_items: int,
    visible_rows: int,
    row_h: int,
    row_gap: int,
    font_hint: pygame.font.Font,
) -> None:
    if scroll > 0:
        up = font_hint.render(" ", True, C_HINT)
        screen.blit(up, (mx + mw - 30, y - 4))
    if scroll + visible_rows < total_items:
        bottom_y = y + visible_rows * (row_h + row_gap) - 18
        dn = font_hint.render(" ", True, C_HINT)
        screen.blit(dn, (mx + mw - 30, bottom_y))
