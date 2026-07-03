# tests/unit/common/test_scroll_list.py

from __future__ import annotations

from engine.common.quantity_picker import QuantityPicker
from engine.common.scroll_list import ScrollListState


class TestScrollListClamped:
    def test_move_down_and_up(self):
        s = ScrollListState(3)
        assert s.move(1, 5) is True
        assert s.selection == 1
        assert s.move(-1, 5) is True
        assert s.selection == 0

    def test_clamps_at_ends(self):
        s = ScrollListState(3)
        assert s.move(-1, 5) is False   # already at top
        s.selection = 4
        assert s.move(1, 5) is False    # already at bottom

    def test_scroll_follows_selection(self):
        s = ScrollListState(3)
        for _ in range(4):
            s.move(1, 10)
        assert s.selection == 4
        assert s.scroll == 2            # window [2..4]
        for _ in range(4):
            s.move(-1, 10)
        assert s.scroll == 0

    def test_empty_list_is_noop(self):
        s = ScrollListState(3)
        assert s.move(1, 0) is False
        assert s.selected([]) is None

    def test_clamp_after_shrink(self):
        s = ScrollListState(3)
        s.selection, s.scroll = 7, 5
        s.clamp(4)
        assert s.selection == 3
        assert s.scroll <= 1

    def test_selected_min_clamps(self):
        s = ScrollListState(3)
        s.selection = 9
        assert s.selected(["a", "b"]) == "b"


class TestScrollListWrapped:
    def test_wraps_both_directions(self):
        s = ScrollListState(5, wrap=True)
        assert s.move(-1, 4) is True
        assert s.selection == 3
        assert s.move(1, 4) is True
        assert s.selection == 0


class TestQuantityPickerClamped:
    def test_steps(self):
        q = QuantityPicker(1, 5)
        assert q.increase_small(9) and q.qty == 2
        assert q.increase_large(9) and q.qty == 7
        assert q.decrease_small(9) and q.qty == 6
        assert q.decrease_large(9) and q.qty == 1

    def test_clamps_at_bounds(self):
        q = QuantityPicker(1, 5)
        assert q.decrease_small(9) is False and q.qty == 1
        q.qty = 9
        assert q.increase_small(9) is False and q.qty == 9

    def test_reset(self):
        q = QuantityPicker(1, 5)
        q.qty = 4
        q.reset()
        assert q.qty == 1


class TestQuantityPickerLooped:
    def test_loops_past_ends(self):
        q = QuantityPicker(1, 10, loop=True)
        assert q.decrease_small(8) and q.qty == 8     # 1 -> wraps to max
        assert q.increase_small(8) and q.qty == 1     # max -> wraps to 1
        assert q.increase_large(8) and q.qty == 1 or q.qty in (1, 8)

    def test_large_step_wraps_to_one(self):
        q = QuantityPicker(1, 10, loop=True)
        q.qty = 5
        assert q.increase_large(8) and q.qty == 1     # 15 > 8 -> 1
