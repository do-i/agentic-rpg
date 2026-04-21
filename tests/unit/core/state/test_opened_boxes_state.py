# tests/unit/core/state/test_opened_boxes_state.py

from engine.common.opened_boxes_state import OpenedBoxesState


class TestOpenedBoxesState:
    def test_empty_by_default(self):
        state = OpenedBoxesState()
        assert state.is_opened("map_a", "box_1") is False

    def test_mark_opened(self):
        state = OpenedBoxesState()
        state.mark_opened("map_a", "box_1")
        assert state.is_opened("map_a", "box_1") is True

    def test_mark_is_per_map(self):
        state = OpenedBoxesState()
        state.mark_opened("map_a", "chest")
        assert state.is_opened("map_a", "chest") is True
        assert state.is_opened("map_b", "chest") is False

    def test_mark_idempotent(self):
        state = OpenedBoxesState()
        state.mark_opened("map_a", "box_1")
        state.mark_opened("map_a", "box_1")
        assert state.to_list() == ["map_a:box_1"]


class TestSerialization:
    def test_to_list_sorted(self):
        state = OpenedBoxesState()
        state.mark_opened("zone_02", "b")
        state.mark_opened("zone_01", "a")
        assert state.to_list() == ["zone_01:a", "zone_02:b"]

    def test_round_trip(self):
        state = OpenedBoxesState()
        state.mark_opened("m", "b1")
        state.mark_opened("m", "b2")
        rebuilt = OpenedBoxesState.from_list(state.to_list())
        assert rebuilt.is_opened("m", "b1")
        assert rebuilt.is_opened("m", "b2")
        assert not rebuilt.is_opened("m", "b3")

    def test_from_list_ignores_malformed(self):
        state = OpenedBoxesState.from_list(["map_a:box_1", "no_colon", ""])
        assert state.is_opened("map_a", "box_1")
        assert state.to_list() == ["map_a:box_1"]

    def test_from_list_none_safe(self):
        state = OpenedBoxesState.from_list(None)
        assert state.to_list() == []
