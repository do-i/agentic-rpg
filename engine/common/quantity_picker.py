# engine/common/quantity_picker.py
#
# Quantity-selection state shared by the shop family. Scenes keep their
# own key mapping (which arrow means +/- differs by shop) and call the
# semantic step methods here.

from __future__ import annotations


class QuantityPicker:
    """A 1..max quantity cursor with small/large steps.

    `loop=True` wraps past the ends (magic-core shop); the default clamps
    to [1, max_qty] (item shop).
    """

    def __init__(self, step_small: int, step_large: int, *, loop: bool = False) -> None:
        self._step_small = step_small
        self._step_large = step_large
        self._loop = loop
        self.qty = 1

    def reset(self) -> None:
        self.qty = 1

    def increase_small(self, max_qty: int) -> bool:
        return self._adjust(self._step_small, max_qty)

    def decrease_small(self, max_qty: int) -> bool:
        return self._adjust(-self._step_small, max_qty)

    def increase_large(self, max_qty: int) -> bool:
        return self._adjust(self._step_large, max_qty)

    def decrease_large(self, max_qty: int) -> bool:
        return self._adjust(-self._step_large, max_qty)

    def _adjust(self, delta: int, max_qty: int) -> bool:
        old = self.qty
        qty = self.qty + delta
        if self._loop:
            if qty < 1:
                qty = max_qty
            elif qty > max_qty:
                qty = 1
        else:
            qty = max(1, min(max_qty, qty))
        self.qty = qty
        return self.qty != old
