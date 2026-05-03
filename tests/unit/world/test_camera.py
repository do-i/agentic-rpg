# tests/unit/world/test_camera.py

from __future__ import annotations

import pytest
from engine.world.camera import Camera
from engine.world.position_data import Position


SCREEN_W = 1280
SCREEN_H = 766

# Map larger than viewport to allow camera movement
MAP_W = SCREEN_W * 3   # 3840
MAP_H = SCREEN_H * 3   # 2298


def make_camera() -> Camera:
    return Camera(MAP_W, MAP_H, SCREEN_W, SCREEN_H)


# ── Construction ──────────────────────────────────────────────

class TestCameraInit:
    def test_offset_starts_at_zero(self):
        c = make_camera()
        assert c.offset_x == 0
        assert c.offset_y == 0


# ── update ────────────────────────────────────────────────────

class TestUpdate:
    def test_centers_on_player(self):
        c = make_camera()
        c.update(Position(SCREEN_W, SCREEN_H))
        assert c.offset_x == SCREEN_W // 2
        assert c.offset_y == SCREEN_H // 2

    def test_clamps_left_edge(self):
        c = make_camera()
        c.update(Position(0, 0))
        assert c.offset_x == 0

    def test_clamps_top_edge(self):
        c = make_camera()
        c.update(Position(0, 0))
        assert c.offset_y == 0

    def test_clamps_right_edge(self):
        c = make_camera()
        c.update(Position(MAP_W, MAP_H // 2))
        assert c.offset_x == MAP_W - SCREEN_W

    def test_clamps_bottom_edge(self):
        c = make_camera()
        c.update(Position(MAP_W // 2, MAP_H))
        assert c.offset_y == MAP_H - SCREEN_H

    def test_player_near_center_moves_camera(self):
        c = make_camera()
        mid_x = MAP_W // 2
        mid_y = MAP_H // 2
        c.update(Position(mid_x, mid_y))
        assert c.offset_x == mid_x - SCREEN_W // 2
        assert c.offset_y == mid_y - SCREEN_H // 2

    def test_small_map_centers_on_screen(self):
        # map smaller than viewport — offset is negative so map renders centered
        small_cam = Camera(SCREEN_W // 2, SCREEN_H // 2, SCREEN_W, SCREEN_H)
        small_cam.update(Position(100, 100))
        assert small_cam.offset_x == (SCREEN_W // 2 - SCREEN_W) // 2
        assert small_cam.offset_y == (SCREEN_H // 2 - SCREEN_H) // 2


# ── apply ─────────────────────────────────────────────────────

class TestApply:
    def test_apply_with_zero_offset(self):
        c = make_camera()
        assert c.apply(100, 200) == (100, 200)

    def test_apply_subtracts_offset(self):
        c = make_camera()
        c.update(Position(SCREEN_W, SCREEN_H))
        sx, sy = c.apply(SCREEN_W, SCREEN_H)
        assert sx == SCREEN_W - c.offset_x
        assert sy == SCREEN_H - c.offset_y

    def test_apply_returns_tuple(self):
        c = make_camera()
        result = c.apply(0, 0)
        assert isinstance(result, tuple)
        assert len(result) == 2
