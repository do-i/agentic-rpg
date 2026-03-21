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
        color_disabled: tuple = (90, 90, 80),
        line_height: int = 48,
    ) -> None:
        self._items = items
        self._font = font
        self._color_normal = color_normal
        self._color_selected = color_selected
        self._color_disabled = color_disabled
        self._line_height = line_height
        self._selected = 0
        self._disabled: set[str] = set()

    def set_item_disabled(self, item: str, disabled: bool) -> None:
        if disabled:
            self._disabled.add(item)
        else:
            self._disabled.discard(item)

    @property
    def selected_index(self) -> int:
        return self._selected

    @property
    def selected_item(self) -> str:
        return self._items[self._selected]

    def handle_events(self, events: list[pygame.event.Event]) -> bool:
        """Returns True if a non-disabled item was confirmed."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self._move(-1)
                elif event.key == pygame.K_DOWN:
                    self._move(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.selected_item not in self._disabled:
                        return True
        return False

    def _move(self, delta: int) -> None:
        total = len(self._items)
        self._selected = (self._selected + delta) % total

    def render(self, screen: pygame.Surface, x: int, y: int) -> None:
        for i, item in enumerate(self._items):
            is_selected = (i == self._selected)
            is_disabled = item in self._disabled

            if is_disabled:
                color = self._color_disabled
            elif is_selected:
                color = self._color_selected
            else:
                color = self._color_normal

            if is_selected and not is_disabled:
                cursor = self._font.render("▶", True, color)
                screen.blit(cursor, (x, y + i * self._line_height))

            text = self._font.render(item, True, color)
            screen.blit(text, (x + 40, y + i * self._line_height))
