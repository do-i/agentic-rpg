# engine/common/scroll_list.py
#
# Selection + scroll-window state for a vertical list menu. Extracted from
# the shop family, which each hand-rolled _list_sel/_scroll/_clamp_scroll;
# other scroll sites (load-game, save modal, item view) can migrate
# opportunistically.

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")


class ScrollListState:
    """Cursor + scroll offset for a list rendered `visible_rows` at a time.

    `wrap=True` makes the cursor loop past the ends (used by short,
    unscrolled lists like the magic-core shop); the default clamps.
    """

    def __init__(self, visible_rows: int, *, wrap: bool = False) -> None:
        self._visible_rows = visible_rows
        self._wrap = wrap
        self.selection = 0
        self.scroll = 0

    def move(self, delta: int, count: int) -> bool:
        """Move the cursor by `delta` in a list of `count` items.
        Returns True when the selection actually changed (hover SFX cue)."""
        if count <= 0:
            return False
        old = self.selection
        if self._wrap:
            self.selection = (self.selection + delta) % count
        else:
            self.selection = max(0, min(count - 1, self.selection + delta))
        self._clamp_scroll(count)
        return self.selection != old

    def clamp(self, count: int) -> None:
        """Re-clamp after the underlying list shrank (e.g. item sold out)."""
        if count > 0:
            self.selection = max(0, min(self.selection, count - 1))
        else:
            self.selection = 0
        self._clamp_scroll(count)

    def reset(self) -> None:
        self.selection = 0
        self.scroll = 0

    def selected(self, items: Sequence[T]) -> T | None:
        if not items:
            return None
        return items[min(self.selection, len(items) - 1)]

    def _clamp_scroll(self, count: int) -> None:
        if self.selection < self.scroll:
            self.scroll = self.selection
        elif self.selection >= self.scroll + self._visible_rows:
            self.scroll = self.selection - self._visible_rows + 1
        max_scroll = max(0, count - self._visible_rows)
        self.scroll = max(0, min(self.scroll, max_scroll))
