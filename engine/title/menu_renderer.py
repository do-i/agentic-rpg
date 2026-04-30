# engine/title/menu_renderer.py

from __future__ import annotations

import pygame


_DEFAULT_CURSOR_W = 40
_CURSOR_PAD = 10


class Menu:
    def __init__(
        self,
        items: list[str],
        font: pygame.font.Font,
        color_normal: tuple = (220, 220, 180),
        color_selected: tuple = (255, 220, 50),
        color_disabled: tuple = (90, 90, 80),
        line_height: int = 48,
        *,
        sfx_manager,
        cursor_icon: pygame.Surface | None = None,
    ) -> None:
        self._items = items
        self._font = font
        self._color_normal = color_normal
        self._color_selected = color_selected
        self._color_disabled = color_disabled
        self._line_height = line_height
        self._selected = 0
        self._disabled: set[str] = set()
        self._sfx_manager = sfx_manager
        self._cursor_icon = cursor_icon

    @property
    def cursor_width(self) -> int:
        if self._cursor_icon is not None:
            return self._cursor_icon.get_width() + _CURSOR_PAD
        return _DEFAULT_CURSOR_W

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
                        self._sfx_manager.play("confirm")
                        return True
        return False

    def _move(self, delta: int) -> None:
        total = len(self._items)
        old = self._selected
        self._selected = (self._selected + delta) % total
        if self._selected != old:
            self._sfx_manager.play("hover")

    def render(self, screen: pygame.Surface, x: int, y: int) -> None:
        text_x = x + self.cursor_width
        for i, item in enumerate(self._items):
            is_selected = (i == self._selected)
            is_disabled = item in self._disabled

            if is_disabled:
                color = self._color_disabled
            elif is_selected:
                color = self._color_selected
            else:
                color = self._color_normal

            line_y = y + i * self._line_height

            if is_selected and not is_disabled and self._cursor_icon is not None:
                ch = self._cursor_icon.get_height()
                line_h = self._font.get_height()
                iy = line_y + (line_h - ch) // 2
                screen.blit(self._cursor_icon, (x, iy))

            text = self._font.render(item, True, color)
            screen.blit(text, (text_x, line_y))
