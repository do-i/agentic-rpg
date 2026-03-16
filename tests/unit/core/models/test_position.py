# tests/unit/core/models/test_position.py

import math
import pytest
from engine.core.models.position import Position


# ── Construction ──────────────────────────────────────────────

class TestPositionInit:
    def test_stores_x_and_y(self):
        p = Position(3, 7)
        assert p.x == 3
        assert p.y == 7

    def test_zero_origin(self):
        p = Position(0, 0)
        assert p.x == 0
        assert p.y == 0

    def test_negative_coordinates(self):
        p = Position(-5, -3)
        assert p.x == -5
        assert p.y == -3


# ── Immutability ──────────────────────────────────────────────

class TestImmutability:
    def test_cannot_set_x(self):
        p = Position(1, 2)
        with pytest.raises(AttributeError):
            p.x = 99

    def test_cannot_set_y(self):
        p = Position(1, 2)
        with pytest.raises(AttributeError):
            p.y = 99

    def test_cannot_set_arbitrary_attr(self):
        p = Position(1, 2)
        with pytest.raises(AttributeError):
            p.z = 0


# ── distance_to ───────────────────────────────────────────────

class TestDistanceTo:
    def test_same_position_is_zero(self):
        p = Position(3, 4)
        assert p.distance_to(p) == 0.0

    def test_horizontal_distance(self):
        a = Position(0, 0)
        b = Position(5, 0)
        assert a.distance_to(b) == 5.0

    def test_vertical_distance(self):
        a = Position(0, 0)
        b = Position(0, 4)
        assert a.distance_to(b) == 4.0

    def test_pythagorean_triple(self):
        # 3-4-5 triangle
        a = Position(0, 0)
        b = Position(3, 4)
        assert a.distance_to(b) == 5.0

    def test_symmetry(self):
        a = Position(1, 2)
        b = Position(4, 6)
        assert a.distance_to(b) == pytest.approx(b.distance_to(a))

    def test_returns_float(self):
        a = Position(0, 0)
        b = Position(1, 1)
        assert isinstance(a.distance_to(b), float)


# ── offset ────────────────────────────────────────────────────

class TestOffset:
    def test_positive_offset(self):
        p = Position(2, 3)
        assert p.offset(1, 1) == Position(3, 4)

    def test_negative_offset(self):
        p = Position(5, 5)
        assert p.offset(-2, -3) == Position(3, 2)

    def test_zero_offset_returns_equal(self):
        p = Position(4, 4)
        assert p.offset(0, 0) == p

    def test_returns_new_instance(self):
        p = Position(1, 1)
        q = p.offset(1, 0)
        assert q is not p

    def test_original_unchanged(self):
        p = Position(1, 1)
        p.offset(5, 5)
        assert p.x == 1 and p.y == 1


# ── Equality and hashing ──────────────────────────────────────

class TestEquality:
    def test_equal_positions(self):
        assert Position(3, 4) == Position(3, 4)

    def test_different_positions(self):
        assert Position(1, 2) != Position(2, 1)

    def test_not_equal_to_non_position(self):
        assert Position(1, 2) != (1, 2)

    def test_hashable(self):
        p = Position(1, 2)
        assert isinstance(hash(p), int)

    def test_usable_as_dict_key(self):
        d = {Position(0, 0): "origin"}
        assert d[Position(0, 0)] == "origin"

    def test_usable_in_set(self):
        s = {Position(1, 1), Position(1, 1), Position(2, 2)}
        assert len(s) == 2


# ── Serialization ─────────────────────────────────────────────

class TestSerialization:
    def test_to_list(self):
        assert Position(5, 3).to_list() == [5, 3]

    def test_from_list(self):
        assert Position.from_list([5, 3]) == Position(5, 3)

    def test_round_trip(self):
        p = Position(7, 12)
        assert Position.from_list(p.to_list()) == p