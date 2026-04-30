# tests/unit/core/world/test_player.py

from __future__ import annotations

import math
import pytest
import pygame
from engine.world.player import Player, PLAYER_SPEED, PLAYER_WIDTH, PLAYER_HEIGHT, COLLISION_W, COLLISION_H, COLLISION_OFFSET_X, COLLISION_OFFSET_Y
from engine.world.position_data import Position


# ── Helpers ───────────────────────────────────────────────────

TS = 32

MAP_W = 640
MAP_H = 480


def make_keys(up=False, down=False, left=False, right=False) -> dict:
    """Fake key state — only movement keys needed."""
    return {
        pygame.K_UP:    up,
        pygame.K_DOWN:  down,
        pygame.K_LEFT:  left,
        pygame.K_RIGHT: right,
    }

def make_player(tile_x: int = 5, tile_y: int = 5, sprite_sheet=None) -> Player:
    """Create a Player starting at the center of the given tile."""
    return Player(
        start=Position(tile_x, tile_y),
        map_width_px=MAP_W,
        map_height_px=MAP_H,
        sprite_sheet=sprite_sheet,
    )

# ── Construction ──────────────────────────────────────────────

class TestPlayerInit:
    def test_pixel_position_derived_from_tile(self):
        p = make_player(tile_x=3, tile_y=4)
        ts = TS
        expected_x = 3 * ts + ts // 2 - COLLISION_OFFSET_X - COLLISION_W // 2
        expected_y = 4 * ts + ts // 2 - COLLISION_OFFSET_Y - COLLISION_H // 2

        assert p.pixel_position.x == expected_x
        assert p.pixel_position.y == expected_y


    def test_origin_tile_maps_to_correct_starting_pixel(self):
        """Tile (0, 0) should place the player so its collision rect starts near (0, 0)."""
        p = make_player(tile_x=0, tile_y=0)

        ts = TS
        expected_x = 0 * ts + ts // 2 - COLLISION_OFFSET_X - COLLISION_W // 2
        expected_y = 0 * ts + ts // 2 - COLLISION_OFFSET_Y - COLLISION_H // 2

        assert p.pixel_position.x == expected_x
        assert p.pixel_position.y == expected_y
        

# ── Movement ──────────────────────────────────────────────────

class TestMovement:
    def test_no_keys_no_movement(self):
        p = make_player()
        before = p.pixel_position
        p.update(make_keys())
        assert p.pixel_position == before

    def test_move_up(self):
        p = make_player()
        before_y = p.pixel_position.y
        p.update(make_keys(up=True))
        assert p.pixel_position.y == before_y - PLAYER_SPEED

    def test_move_down(self):
        p = make_player()
        before_y = p.pixel_position.y
        p.update(make_keys(down=True))
        assert p.pixel_position.y == before_y + PLAYER_SPEED

    def test_move_left(self):
        p = make_player()
        before_x = p.pixel_position.x
        p.update(make_keys(left=True))
        assert p.pixel_position.x == before_x - PLAYER_SPEED

    def test_move_right(self):
        p = make_player()
        before_x = p.pixel_position.x
        p.update(make_keys(right=True))
        assert p.pixel_position.x == before_x + PLAYER_SPEED


# ── Diagonal movement ─────────────────────────────────────────

class TestDiagonal:
    def test_diagonal_is_slower_than_cardinal(self):
        p_diag = make_player()
        p_card = make_player()

        p_diag.update(make_keys(up=True, right=True))
        p_card.update(make_keys(right=True))

        diag_dx = abs(p_diag.pixel_position.x - make_player().pixel_position.x)
        card_dx = abs(p_card.pixel_position.x - make_player().pixel_position.x)
        assert diag_dx < card_dx

    def test_opposite_keys_cancel(self):
        p = make_player()
        before = p.pixel_position
        p.update(make_keys(left=True, right=True))
        assert p.pixel_position == before



# ── Bounds clamping ───────────────────────────────────────────
class TestBounds:
    def test_cannot_move_left_of_map(self):
        p = make_player(tile_x=0, tile_y=5)
        for _ in range(50):
            p.update(make_keys(left=True))
        assert p.pixel_position.x >= -50

    def test_cannot_move_above_map(self):
        p = make_player(tile_x=5, tile_y=0)
        for _ in range(50):
            p.update(make_keys(up=True))
        assert p.pixel_position.y >= -60

    def test_cannot_move_right_of_map(self):
        p = make_player(tile_x=0, tile_y=0)
        for _ in range(1000):
            p.update(make_keys(right=True))
        # Player can go a bit beyond due to collision offset + centering
        assert p.pixel_position.x <= MAP_W - PLAYER_WIDTH + 30, \
            f"Player went too far right: {p.pixel_position.x} (max allowed {MAP_W - PLAYER_WIDTH + 30})"

    def test_cannot_move_below_map(self):
        p = make_player(tile_x=0, tile_y=0)
        for _ in range(1000):
            p.update(make_keys(down=True))
        assert p.pixel_position.y <= MAP_H - PLAYER_HEIGHT + 30, \
            f"Player went too far down: {p.pixel_position.y} (max allowed {MAP_H - PLAYER_HEIGHT + 30})"


