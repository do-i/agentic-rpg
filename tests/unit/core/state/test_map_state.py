# tests/unit/state/test_map_state.py

import pytest
from engine.common.position_data import Position
from engine.common.map_state import MapState


# ── Construction ──────────────────────────────────────────────

class TestMapStateInit:
    def test_defaults(self):
        s = MapState()
        assert s.current == ""
        assert s.position == Position(0, 0)
        assert s.visited == []

    def test_with_values(self, map_state):
        assert map_state.current == "town_01"
        assert map_state.position == Position(5, 3)
        assert "zone_01" in map_state.visited


# ── move_to ───────────────────────────────────────────────────

class TestMoveTo:
    def test_updates_current_and_position(self, empty_map_state):
        empty_map_state.move_to("town_01", Position(10, 5))
        assert empty_map_state.current == "town_01"
        assert empty_map_state.position == Position(10, 5)

    def test_records_previous_map_as_visited(self):
        s = MapState(current="zone_01", position=Position(0, 0))
        s.move_to("town_01", Position(5, 5))
        assert s.has_visited("zone_01")

    def test_does_not_record_empty_current(self, empty_map_state):
        empty_map_state.move_to("town_01", Position(0, 0))
        assert empty_map_state.visited == []

    def test_no_duplicate_in_visited(self):
        s = MapState(current="zone_01", position=Position(0, 0))
        s.move_to("town_01", Position(0, 0))
        s.move_to("zone_01", Position(0, 0))  # back to zone_01
        s.move_to("town_01", Position(0, 0))  # town_01 again
        assert s.visited.count("town_01") == 1


# ── set_position ──────────────────────────────────────────────

class TestSetPosition:
    def test_updates_position_within_current_map(self, map_state):
        map_state.set_position(Position(99, 99))
        assert map_state.position == Position(99, 99)

    def test_does_not_change_current_map(self, map_state):
        map_state.set_position(Position(1, 1))
        assert map_state.current == "town_01"


# ── has_visited ───────────────────────────────────────────────

class TestHasVisited:
    def test_true_for_visited_map(self, map_state):
        assert map_state.has_visited("zone_01")

    def test_false_for_unvisited_map(self, map_state):
        assert not map_state.has_visited("dungeon_99")

    def test_false_for_current_map(self, map_state):
        # current map is not in visited until we move away
        assert not map_state.has_visited("town_01")


# ── Serialization ─────────────────────────────────────────────

class TestSerialization:
    def test_to_dict(self, map_state):
        d = map_state.to_dict()
        assert d["current"] == "town_01"
        assert d["position"] == [5, 3]
        assert "zone_01" in d["visited"]

    def test_round_trip(self, map_state):
        restored = MapState.from_dict(map_state.to_dict())
        assert restored.current == map_state.current
        assert restored.position == map_state.position
        assert restored.visited == map_state.visited

    def test_from_dict_defaults(self):
        s = MapState.from_dict({})
        assert s.current == ""
        assert s.position == Position(0, 0)
        assert s.visited == []