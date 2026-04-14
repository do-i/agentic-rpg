# tests/unit/core/encounter/test_enemy_sprite.py

import pytest
from unittest.mock import MagicMock

from engine.encounter.enemy_sprite import (
    EnemySprite,
    COLLISION_OFFSET_X, COLLISION_OFFSET_Y, COLLISION_W, COLLISION_H,
)
from engine.world.sprite_sheet import Direction


def make_sprite(formation=None, tile_x=5, tile_y=5, is_boss=False,
                chase_range=0, tile_size=32) -> EnemySprite:
    return EnemySprite(
        formation=formation or ["goblin"],
        tile_x=tile_x,
        tile_y=tile_y,
        is_boss=is_boss,
        chase_range=chase_range,
        tile_size=tile_size,
    )


class TestCollisionRect:
    def test_rect_uses_correct_offset(self):
        sprite = make_sprite(tile_x=0, tile_y=0, tile_size=32)
        cx, cy, cw, ch = sprite.collision_rect
        assert cx == COLLISION_OFFSET_X
        assert cy == COLLISION_OFFSET_Y
        assert cw == COLLISION_W
        assert ch == COLLISION_H

    def test_rect_moves_with_position(self):
        sprite = make_sprite(tile_x=3, tile_y=2, tile_size=32)
        cx, cy, _, _ = sprite.collision_rect
        assert cx == 3 * 32 + COLLISION_OFFSET_X
        assert cy == 2 * 32 + COLLISION_OFFSET_Y


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
        sprite = make_sprite(tile_x=0, tile_y=3, tile_size=32)
        assert sprite.pixel_y == 3 * 32
