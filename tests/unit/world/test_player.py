# tests/unit/core/world/test_player.py

import math
import pytest
import pygame
from engine.world.player import Player, PLAYER_SPEED, PLAYER_SIZE
from engine.core.models.position import Position
from engine.core.settings import Settings


# ── Helpers ───────────────────────────────────────────────────

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


def make_player(tile_x: int = 5, tile_y: int = 5) -> Player:
    return Player(Position(tile_x, tile_y), MAP_W, MAP_H)


# ── Construction ──────────────────────────────────────────────

class TestPlayerInit:
    def test_pixel_position_derived_from_tile(self):
        p = make_player(tile_x=3, tile_y=4)
        assert p.pixel_position.x == 3 * Settings.TILE_SIZE
        assert p.pixel_position.y == 4 * Settings.TILE_SIZE

    def test_origin_tile_maps_to_zero_pixels(self):
        p = make_player(tile_x=0, tile_y=0)
        assert p.pixel_position == Position(0, 0)


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
        p = Player(Position(0, 5), MAP_W, MAP_H)
        for _ in range(20):
            p.update(make_keys(left=True))
        assert p.pixel_position.x >= 0

    def test_cannot_move_above_map(self):
        p = Player(Position(5, 0), MAP_W, MAP_H)
        for _ in range(20):
            p.update(make_keys(up=True))
        assert p.pixel_position.y >= 0

    def test_cannot_move_right_of_map(self):
        p = Player(Position(0, 0), MAP_W, MAP_H)
        for _ in range(1000):
            p.update(make_keys(right=True))
        assert p.pixel_position.x <= MAP_W - PLAYER_SIZE

    def test_cannot_move_below_map(self):
        p = Player(Position(0, 0), MAP_W, MAP_H)
        for _ in range(1000):
            p.update(make_keys(down=True))
        assert p.pixel_position.y <= MAP_H - PLAYER_SIZE