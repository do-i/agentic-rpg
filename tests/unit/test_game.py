from __future__ import annotations

from engine.game import Game


def _game_with_speed(speed: float) -> Game:
    game = Game.__new__(Game)
    game._playback_speed = speed
    game._playback_accumulator = 0.0
    return game


def test_playback_steps_support_half_speed():
    game = _game_with_speed(0.5)

    assert [game._playback_steps_this_frame() for _ in range(4)] == [0, 1, 0, 1]


def test_playback_steps_support_fractional_fast_speed():
    game = _game_with_speed(1.5)

    assert [game._playback_steps_this_frame() for _ in range(4)] == [1, 2, 1, 2]


def test_playback_steps_support_integer_fast_speed():
    game = _game_with_speed(2.0)

    assert [game._playback_steps_this_frame() for _ in range(3)] == [2, 2, 2]
