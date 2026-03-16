# engine/ui/menu.py

import pygame
from engine.core.settings import Settings


class Menu:
    def __init__(
        self,
        items: list[str],
        font: pygame.font.Font,
        color_normal: tuple = (220, 220, 180),
        color_selected: tuple = (255, 220, 50),
        line_height: int = 48,
    ) -> None:
        self._items = items
        self._font = font
        self._color_normal = color_normal
        self._color_selected = color_selected
        self._line_height = line_height
        self._selected = 0

    @property
    def selected_index(self) -> int:
        return self._selected

    @property
    def selected_item(self) -> str:
        return self._items[self._selected]

    def handle_events(self, events: list[pygame.event.Event]) -> bool:
        """Returns True if item was confirmed."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self._selected = (self._selected - 1) % len(self._items)
                elif event.key == pygame.K_DOWN:
                    self._selected = (self._selected + 1) % len(self._items)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return True
        return False

    def render(self, screen: pygame.Surface, x: int, y: int) -> None:
        for i, item in enumerate(self._items):
            color = self._color_selected if i == self._selected else self._color_normal
            # cursor at fixed x, text at fixed x+24
            if i == self._selected:
                cursor = self._font.render("▶", True, color)
                screen.blit(cursor, (x, y + i * self._line_height))
            text = self._font.render(item, True, color)
            screen.blit(text, (x + 40, y + i * self._line_height))
