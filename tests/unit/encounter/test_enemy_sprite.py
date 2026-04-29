# tests/unit/core/encounter/test_enemy_sprite.py

import pytest
from unittest.mock import MagicMock, patch

from engine.encounter.enemy_sprite import (
    EnemySprite, _direction_toward,
    COLLISION_OFFSET_X, COLLISION_OFFSET_Y, COLLISION_W, COLLISION_H,
    IDLE_FRAME, WALK_START, WALK_END, BASE_FRAME_DUR,
)
from engine.world.sprite_sheet import Direction
from engine.util.pseudo_random import PseudoRandom

_rng = PseudoRandom(seed=0)


def make_sprite(formation=None, tile_x=5, tile_y=5, is_boss=False,
                chase_range=0, tile_size=32) -> EnemySprite:
    return EnemySprite(
        formation=formation or ["goblin"],
        tile_x=tile_x,
        tile_y=tile_y,
        is_boss=is_boss,
        chase_range=chase_range,
        tile_size=tile_size,
        rng=_rng,
    )


class TestCollisionRect:
    def test_rect_centered_on_tile(self):
        # Sprite origin is shifted so the collision rect center lands on the tile center.
        ts = 32
        sprite = make_sprite(tile_x=0, tile_y=0, tile_size=ts)
        cx, cy, cw, ch = sprite.collision_rect
        assert cx + cw // 2 == ts // 2   # horizontally centered on tile
        assert cy + ch // 2 == ts // 2   # vertically centered on tile
        assert cw == COLLISION_W
        assert ch == COLLISION_H

    def test_rect_moves_with_tile(self):
        ts = 32
        sprite = make_sprite(tile_x=3, tile_y=2, tile_size=ts)
        cx, cy, cw, ch = sprite.collision_rect
        assert cx + cw // 2 == 3 * ts + ts // 2   # centered on tile (3,2) x
        assert cy + ch // 2 == 2 * ts + ts // 2   # centered on tile (3,2) y


class TestCollidesWith:
    def test_overlapping_rect_returns_true(self):
        sprite = make_sprite(tile_x=0, tile_y=0)
        cx, cy, cw, ch = sprite.collision_rect
        # Rect that exactly overlaps
        assert sprite.collides_with((cx, cy, cw, ch))

    def test_non_overlapping_rect_returns_false(self):
        sprite = make_sprite(tile_x=0, tile_y=0)
        assert not sprite.collides_with((9999, 9999, 10, 10))

    def test_adjacent_rect_does_not_collide(self):
        sprite = make_sprite(tile_x=0, tile_y=0)
        cx, cy, cw, ch = sprite.collision_rect
        assert not sprite.collides_with((cx + cw, cy, 10, 10))


class TestBossStaysStationary:
    def test_boss_does_not_move_when_updated(self):
        sprite = make_sprite(tile_x=5, tile_y=5, is_boss=True, chase_range=10)
        initial_px = sprite._px
        initial_py = sprite._py
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite.update(1.0, 0.0, 0.0, collision, [], effective_chase_range=10)
        assert sprite._px == initial_px
        assert sprite._py == initial_py


class TestStateTransitions:
    def test_wanders_when_player_out_of_range(self):
        sprite = make_sprite(tile_x=5, tile_y=5, chase_range=3, tile_size=32)
        # Player is far away (100 tiles)
        player_px = 5 * 32 + 100 * 32
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite.update(0.016, player_px, 5 * 32, collision, [], effective_chase_range=3)
        assert sprite._state == "wandering"

    def test_chases_when_player_in_range(self):
        sprite = make_sprite(tile_x=5, tile_y=5, chase_range=5, tile_size=32)
        # Player is 2 tiles away (within 5 tile range)
        player_px = float(5 * 32 + 2 * 32)
        player_py = float(5 * 32)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite.update(0.016, player_px, player_py, collision, [], effective_chase_range=5)
        assert sprite._state == "chasing"

    def test_no_chase_when_effective_range_zero(self):
        sprite = make_sprite(tile_x=5, tile_y=5, chase_range=5, tile_size=32)
        # Player is 1 tile away, but effective_chase_range=0 (Rogue reduced it)
        player_px = float(5 * 32 + 1 * 32)
        player_py = float(5 * 32)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite.update(0.016, player_px, player_py, collision, [], effective_chase_range=0)
        assert sprite._state == "wandering"


class TestFormationAndProperties:
    def test_formation_stored(self):
        sprite = make_sprite(formation=["goblin", "goblin_warrier"])
        assert sprite.formation == ["goblin", "goblin_warrier"]

    def test_pixel_y_property(self):
        ts = 32
        sprite = make_sprite(tile_x=0, tile_y=3, tile_size=ts)
        expected = 3 * ts + ts // 2 - COLLISION_OFFSET_Y - COLLISION_H // 2
        assert sprite.pixel_y == expected

    def test_repr_contains_key_fields(self):
        sprite = make_sprite(formation=["goblin"])
        r = repr(sprite)
        assert "EnemySprite" in r
        assert "goblin" in r


# ── _direction_toward ─────────────────────────────────────────

class TestDirectionToward:
    def test_prefers_vertical_when_dy_dominates(self):
        assert _direction_toward(0, 0, 0, 10) == Direction.DOWN

    def test_up_when_player_above(self):
        assert _direction_toward(0, 10, 0, 0) == Direction.UP

    def test_right_when_dx_dominates(self):
        assert _direction_toward(0, 0, 10, 1) == Direction.RIGHT

    def test_left_when_player_left(self):
        assert _direction_toward(10, 0, 0, 1) == Direction.LEFT


# ── Chase edge cases ──────────────────────────────────────────

class TestChaseEdgeCases:
    def test_no_movement_when_player_overlapping(self):
        # dist < 1 → early return, no position change
        sprite = make_sprite(tile_x=5, tile_y=5, chase_range=5)
        px_before = sprite._px
        py_before = sprite._py
        # player is 0.3px away diagonally → dist ≈ 0.42 < 1
        sprite._update_chase(0.016, sprite._px + 0.3, sprite._py + 0.3, None, [])
        assert sprite._px == px_before
        assert sprite._py == py_before

    def test_chase_blocked_by_collision(self):
        sprite = make_sprite(tile_x=5, tile_y=5, chase_range=5)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = True
        px_before = sprite._px
        # Player is far away (10 tiles)
        sprite._update_chase(0.016, sprite._px + 320, sprite._py, collision, [])
        assert sprite._px == px_before  # blocked, no movement

    def test_chase_facing_right_when_dx_dominates(self):
        sprite = make_sprite(tile_x=5, tile_y=5, chase_range=10)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite._update_chase(0.016, sprite._px + 100, sprite._py + 1, collision, [])
        assert sprite._facing_dir == Direction.RIGHT


# ── Wander state machine ──────────────────────────────────────

class TestWanderStateMachine:
    def test_pause_expiry_starts_movement_when_target_found(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        sprite._wander_moving = False
        sprite._wander_pause = 0.0
        with patch.object(sprite, '_pick_wander_target', return_value=True):
            sprite._update_wander(0.001, None, [])
        assert sprite._wander_moving

    def test_pause_expiry_resets_pause_when_no_target(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        sprite._wander_moving = False
        sprite._wander_pause = 0.0
        with patch.object(sprite, '_pick_wander_target', return_value=False):
            sprite._update_wander(0.001, None, [])
        assert not sprite._wander_moving
        assert sprite._wander_pause > 0

    def test_arrival_stops_movement(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        sprite._wander_moving = True
        # Set target at current position → dist == 0 → arrival
        sprite._wander_target_px = int(sprite._px)
        sprite._wander_target_py = int(sprite._py)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite._update_wander(0.016, collision, [])
        assert not sprite._wander_moving
        assert sprite._frame_index == IDLE_FRAME

    def test_moving_advances_position(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        sprite._wander_moving = True
        sprite._wander_target_px = int(sprite._px) + 200
        sprite._wander_target_py = int(sprite._py)
        px_before = sprite._px
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite._update_wander(0.016, collision, [])
        assert sprite._px > px_before

    def test_blocked_movement_stops_wander(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        sprite._wander_moving = True
        sprite._wander_target_px = int(sprite._px) + 200
        sprite._wander_target_py = int(sprite._py)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = True
        sprite._update_wander(0.016, collision, [])
        assert not sprite._wander_moving
        assert sprite._frame_index == IDLE_FRAME


# ── _pick_wander_target ───────────────────────────────────────

class TestPickWanderTarget:
    def test_returns_true_and_sets_target_when_unblocked(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        sprite._rng = MagicMock()
        sprite._rng.randint.return_value = 32
        result = sprite._pick_wander_target(collision, [])
        assert result is True
        assert sprite._wander_target_px is not None
        assert sprite._wander_target_py is not None

    def test_returns_false_when_all_candidates_blocked(self):
        sprite = make_sprite(tile_x=5, tile_y=5)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = True
        result = sprite._pick_wander_target(collision, [])
        assert result is False


# ── _is_blocked ───────────────────────────────────────────────

class TestIsBlocked:
    def test_blocked_by_overlapping_other_rect(self):
        sprite = make_sprite(tile_x=0, tile_y=0)
        # At px=0, py=0: collision area starts at (OFFSET_X, OFFSET_Y)
        cx = COLLISION_OFFSET_X
        cy = COLLISION_OFFSET_Y
        other = [(cx, cy, COLLISION_W, COLLISION_H)]
        assert sprite._is_blocked(0, 0, None, other)

    def test_not_blocked_by_non_overlapping_other_rect(self):
        sprite = make_sprite(tile_x=0, tile_y=0)
        other = [(9999, 9999, 20, 18)]
        assert not sprite._is_blocked(0, 0, None, other)

    def test_blocked_by_collision_map(self):
        sprite = make_sprite(tile_x=0, tile_y=0)
        collision = MagicMock()
        collision.is_rect_blocked.return_value = True
        assert sprite._is_blocked(0, 0, collision, [])


# ── _advance_frame ────────────────────────────────────────────

class TestAdvanceFrame:
    def test_frame_wraps_after_walk_end(self):
        sprite = make_sprite()
        sprite._frame_index = WALK_END
        sprite._frame_timer = BASE_FRAME_DUR  # at threshold
        sprite._advance_frame(0.0)
        assert sprite._frame_index == WALK_START

    def test_no_advance_before_threshold(self):
        sprite = make_sprite()
        sprite._frame_index = WALK_START
        sprite._frame_timer = 0.0
        sprite._advance_frame(BASE_FRAME_DUR * 0.5)  # under threshold
        assert sprite._frame_index == WALK_START
