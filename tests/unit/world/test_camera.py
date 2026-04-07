# tests/unit/world/test_camera.py

import pytest
from engine.world.camera import Camera
from engine.dto.position import Position
from engine.settings import Settings


# ── Helpers ───────────────────────────────────────────────────

# Map larger than viewport to allow camera movement
MAP_W = Settings.SCREEN_WIDTH * 3   # 3840
MAP_H = Settings.SCREEN_HEIGHT * 3  # 2160


def make_camera() -> Camera:
    return Camera(MAP_W, MAP_H)


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
        c.update(Position(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT))
        assert c.offset_x == Settings.SCREEN_WIDTH // 2
        assert c.offset_y == Settings.SCREEN_HEIGHT // 2

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
        assert c.offset_x == MAP_W - Settings.SCREEN_WIDTH

    def test_clamps_bottom_edge(self):
        c = make_camera()
        c.update(Position(MAP_W // 2, MAP_H))
        assert c.offset_y == MAP_H - Settings.SCREEN_HEIGHT

    def test_player_near_center_moves_camera(self):
        c = make_camera()
        mid_x = MAP_W // 2
        mid_y = MAP_H // 2
        c.update(Position(mid_x, mid_y))
        assert c.offset_x == mid_x - Settings.SCREEN_WIDTH // 2
        assert c.offset_y == mid_y - Settings.SCREEN_HEIGHT // 2

    def test_small_map_clamps_both_axes(self):
        # map smaller than viewport — offset should stay at 0
        small_cam = Camera(Settings.SCREEN_WIDTH // 2, Settings.SCREEN_HEIGHT // 2)
        small_cam.update(Position(100, 100))
        assert small_cam.offset_x == 0
        assert small_cam.offset_y == 0


# ── apply ─────────────────────────────────────────────────────

class TestApply:
    def test_apply_with_zero_offset(self):
        c = make_camera()
        assert c.apply(100, 200) == (100, 200)

    def test_apply_subtracts_offset(self):
        c = make_camera()
        c.update(Position(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT))
        sx, sy = c.apply(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        assert sx == Settings.SCREEN_WIDTH - c.offset_x
        assert sy == Settings.SCREEN_HEIGHT - c.offset_y

    def test_apply_returns_tuple(self):
        c = make_camera()
        result = c.apply(0, 0)
        assert isinstance(result, tuple)
        assert len(result) == 2