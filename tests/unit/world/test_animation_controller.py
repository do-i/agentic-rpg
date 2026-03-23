# tests/unit/world/test_animation_controller.py

import pytest
from unittest.mock import MagicMock
import pygame
from engine.world.animation_controller import AnimationController, FRAME_DURATION
from engine.world.sprite_sheet import Direction, FRAMES_PER_ROW


@pytest.fixture
def mock_sheet():
    sheet = MagicMock()
    sheet.frame_count = FRAMES_PER_ROW
    sheet.get_frame.return_value = MagicMock(spec=pygame.Surface)
    return sheet


@pytest.fixture
def controller(mock_sheet):
    return AnimationController(mock_sheet)


# ── Initial state ─────────────────────────────────────────────

class TestInit:
    def test_default_direction_is_down(self, controller):
        assert controller.direction == Direction.DOWN

    def test_default_frame_is_zero(self, controller):
        assert controller._frame_index == 0


# ── Direction update ──────────────────────────────────────────

class TestDirectionUpdate:
    def test_moving_up(self, controller):
        controller.update(0.1, 0, -1)
        assert controller.direction == Direction.UP

    def test_moving_down(self, controller):
        controller.update(0.1, 0, 1)
        assert controller.direction == Direction.DOWN

    def test_moving_left(self, controller):
        controller.update(0.1, -1, 0)
        assert controller.direction == Direction.LEFT

    def test_moving_right(self, controller):
        controller.update(0.1, 1, 0)
        assert controller.direction == Direction.RIGHT

    def test_vertical_priority_over_horizontal(self, controller):
        controller.update(0.1, 1, -1)
        assert controller.direction == Direction.UP

    def test_stationary_keeps_last_direction(self, controller):
        controller.update(0.1, 1, 0)
        controller.update(0.1, 0, 0)
        assert controller.direction == Direction.RIGHT


# ── Frame advance ─────────────────────────────────────────────

class TestFrameAdvance:
    def test_frame_advances_after_duration(self, controller):
        controller.update(FRAME_DURATION, 1, 0)
        assert controller._frame_index == 1

    def test_frame_does_not_advance_before_duration(self, controller):
        controller.update(FRAME_DURATION * 0.5, 1, 0)
        assert controller._frame_index == 0

    def test_frame_wraps_at_end(self, controller):
        for _ in range(FRAMES_PER_ROW):
            controller.update(FRAME_DURATION, 1, 0)
        assert controller._frame_index == 0

    def test_stationary_resets_frame(self, controller):
        controller.update(FRAME_DURATION, 1, 0)
        assert controller._frame_index == 1
        controller.update(0.1, 0, 0)
        assert controller._frame_index == 0

    def test_stationary_resets_timer(self, controller):
        controller.update(FRAME_DURATION * 0.5, 1, 0)
        controller.update(0.1, 0, 0)
        assert controller._timer == 0.0


# ── current_frame ─────────────────────────────────────────────

class TestCurrentFrame:
    def test_returns_surface(self, controller):
        frame = controller.current_frame
        assert frame is not None

    def test_calls_sheet_with_correct_args(self, controller, mock_sheet):
        controller.update(0.1, 0, 1)
        controller.current_frame
        mock_sheet.get_frame.assert_called_with(Direction.DOWN, controller._frame_index)
