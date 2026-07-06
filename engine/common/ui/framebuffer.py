from __future__ import annotations

import pygame


def ensure_framebuffer(
    framebuffer: pygame.Surface | None,
    size: tuple[int, int],
) -> pygame.Surface:
    """Return a software surface matching the display size.

    Scenes render into this normal opaque surface first; the finished frame is
    then copied to the display. That keeps text/panel composition away from
    platform-specific display-surface behavior while preserving a fully opaque
    final frame for menu backdrops.
    """
    if framebuffer is not None and framebuffer.get_size() == size:
        return framebuffer

    surface = pygame.Surface(size)
    if pygame.display.get_surface() is not None:
        return surface.convert()
    return surface


def present_frame(display: pygame.Surface, framebuffer: pygame.Surface) -> None:
    display.blit(framebuffer, (0, 0))
