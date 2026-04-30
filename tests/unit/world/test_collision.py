# tests/unit/world/test_collision.py

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
import pytmx

from engine.world.collision import CollisionMap


# ── Helpers ───────────────────────────────────────────────────

def make_tmx(blocked_tiles: set[tuple[int, int]]) -> pytmx.TiledMap:
    """
    Build a minimal fake TiledMap with one collision layer.
    blocked_tiles: set of (tile_x, tile_y) that are impassable.
    """
    # fake tile layer
    layer = MagicMock(spec=pytmx.TiledTileLayer)
    layer.name = "collision"

    # __iter__ yields (x, y, gid) — gid=1 if blocked, 0 if passable
    all_tiles = []
    for tx in range(20):
        for ty in range(20):
            gid = 1 if (tx, ty) in blocked_tiles else 0
            all_tiles.append((tx, ty, gid))
    layer.__iter__ = MagicMock(return_value=iter(all_tiles))

    tmx = MagicMock(spec=pytmx.TiledMap)
    tmx.layers = [layer]
    return tmx


def make_empty_tmx() -> pytmx.TiledMap:
    return make_tmx(set())


TS = 32


# ── Construction ──────────────────────────────────────────────

class TestCollisionMapInit:
    def test_empty_map_has_no_blocked_tiles(self):
        c = CollisionMap(make_empty_tmx(), TS)
        assert not c.is_blocked(0, 0)

    def test_blocked_tile_is_detected(self):
        c = CollisionMap(make_tmx({(3, 5)}), TS)
        assert c.is_blocked(3, 5)

    def test_unblocked_tile_is_not_blocked(self):
        c = CollisionMap(make_tmx({(3, 5)}), TS)
        assert not c.is_blocked(4, 5)

    def test_multiple_blocked_tiles(self):
        blocked = {(1, 1), (2, 2), (5, 8)}
        c = CollisionMap(make_tmx(blocked), TS)
        for tx, ty in blocked:
            assert c.is_blocked(tx, ty)


# ── is_blocked_px ─────────────────────────────────────────────

class TestIsBlockedPx:
    def test_pixel_maps_to_correct_tile(self):
        c = CollisionMap(make_tmx({(2, 3)}), TS)
        assert c.is_blocked_px(2 * TS, 3 * TS)

    def test_pixel_inside_blocked_tile(self):
        c = CollisionMap(make_tmx({(2, 3)}), TS)
        assert c.is_blocked_px(2 * TS + 10, 3 * TS + 10)

    def test_pixel_outside_blocked_tile(self):
        c = CollisionMap(make_tmx({(2, 3)}), TS)
        assert not c.is_blocked_px(3 * TS, 3 * TS)

    def test_pixel_zero_zero_on_passable(self):
        c = CollisionMap(make_empty_tmx(), TS)
        assert not c.is_blocked_px(0, 0)


# ── is_rect_blocked ───────────────────────────────────────────

class TestIsRectBlocked:
    def test_rect_fully_on_passable(self):
        c = CollisionMap(make_empty_tmx(), TS)
        assert not c.is_rect_blocked(0, 0, 24, 24)

    def test_top_left_corner_blocked(self):
        c = CollisionMap(make_tmx({(0, 0)}), TS)
        assert c.is_rect_blocked(0, 0, 24, 24)

    def test_top_right_corner_blocked(self):
        c = CollisionMap(make_tmx({(1, 0)}), TS)
        # rect from px=16 width=24 → right edge at px=39 → tile 1
        assert c.is_rect_blocked(16, 0, 24, 24)

    def test_bottom_left_corner_blocked(self):
        c = CollisionMap(make_tmx({(0, 1)}), TS)
        assert c.is_rect_blocked(0, 16, 24, 24)

    def test_bottom_right_corner_blocked(self):
        c = CollisionMap(make_tmx({(1, 1)}), TS)
        assert c.is_rect_blocked(16, 16, 24, 24)

    def test_rect_entirely_clear(self):
        c = CollisionMap(make_tmx({(5, 5)}), TS)
        assert not c.is_rect_blocked(0, 0, 24, 24)


# ── Layer name filtering ──────────────────────────────────────

class TestLayerFiltering:
    def test_non_collision_layer_ignored(self):
        layer = MagicMock(spec=pytmx.TiledTileLayer)
        layer.name = "ground"
        layer.__iter__ = MagicMock(return_value=iter([(0, 0, 99)]))

        tmx = MagicMock(spec=pytmx.TiledMap)
        tmx.layers = [layer]

        c = CollisionMap(tmx, TS)
        assert not c.is_blocked(0, 0)

    def test_non_tile_layer_ignored(self):
        obj_layer = MagicMock(spec=pytmx.TiledObjectGroup)
        obj_layer.name = "collision"

        tmx = MagicMock(spec=pytmx.TiledMap)
        tmx.layers = [obj_layer]

        c = CollisionMap(tmx, TS)
        assert not c.is_blocked(0, 0)