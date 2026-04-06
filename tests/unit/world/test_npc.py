# tests/unit/world/test_npc.py

import pytest
from unittest.mock import MagicMock
import pygame
from engine.world.npc import Npc, INTERACTION_RANGE, _direction_toward
from engine.world.sprite_sheet import SpriteSheet, Direction
from engine.core.state.flag_state import FlagState
from engine.core.models.position import Position
from engine.core.settings import Settings


def make_npc(
    tile_x=5, tile_y=5,
    requires=None, excludes=None,
    sprite_sheet=None,
    default_facing="down",
) -> Npc:
    return Npc(
        npc_id="test_npc",
        dialogue_id="test_dialogue",
        tile_x=tile_x,
        tile_y=tile_y,
        present_requires=requires or [],
        present_excludes=excludes or [],
        sprite_sheet=sprite_sheet,
        default_facing=default_facing,
    )


def make_mock_sprite() -> SpriteSheet:
    sheet = MagicMock(spec=SpriteSheet)
    sheet.get_frame.return_value = pygame.Surface((64, 64))
    return sheet


# ── is_present ────────────────────────────────────────────────

class TestIsPresent:
    def test_no_conditions_always_present(self):
        npc = make_npc()
        assert npc.is_present(FlagState())

    def test_requires_met(self):
        npc = make_npc(requires=["flag_a"])
        assert npc.is_present(FlagState({"flag_a"}))

    def test_requires_not_met(self):
        npc = make_npc(requires=["flag_a"])
        assert not npc.is_present(FlagState())

    def test_excludes_blocks(self):
        npc = make_npc(excludes=["flag_a"])
        assert not npc.is_present(FlagState({"flag_a"}))

    def test_excludes_absent_allows(self):
        npc = make_npc(excludes=["flag_a"])
        assert npc.is_present(FlagState())


# ── is_near ───────────────────────────────────────────────────

class TestIsNear:
    def test_same_pixel_position_is_near(self):
        npc = make_npc(tile_x=5, tile_y=5)
        pos = Position(5 * Settings.TILE_SIZE, 5 * Settings.TILE_SIZE)
        assert npc.is_near(pos)

    def test_adjacent_tile_is_near(self):
        npc = make_npc(tile_x=5, tile_y=5)
        pos = Position(6 * Settings.TILE_SIZE, 5 * Settings.TILE_SIZE)
        assert npc.is_near(pos)

    def test_far_position_is_not_near(self):
        npc = make_npc(tile_x=5, tile_y=5)
        pos = Position(20 * Settings.TILE_SIZE, 20 * Settings.TILE_SIZE)
        assert not npc.is_near(pos)

    def test_boundary_just_inside(self):
        npc = make_npc(tile_x=5, tile_y=5)
        npc_px = 5 * Settings.TILE_SIZE
        pos = Position(npc_px + int(INTERACTION_RANGE), npc_px)
        assert npc.is_near(pos)

    def test_boundary_just_outside(self):
        npc = make_npc(tile_x=5, tile_y=5)
        npc_px = 5 * Settings.TILE_SIZE
        pos = Position(npc_px + int(INTERACTION_RANGE) + 1, npc_px)
        assert not npc.is_near(pos)


# ── is_facing_toward ──────────────────────────────────────────

class TestIsFacingToward:
    def test_facing_down_target_below(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="down")
        target = Position(5 * Settings.TILE_SIZE, 6 * Settings.TILE_SIZE)
        assert npc.is_facing_toward(target)

    def test_facing_down_target_above(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="down")
        target = Position(5 * Settings.TILE_SIZE, 4 * Settings.TILE_SIZE)
        assert not npc.is_facing_toward(target)

    def test_facing_up_target_above(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="up")
        target = Position(5 * Settings.TILE_SIZE, 4 * Settings.TILE_SIZE)
        assert npc.is_facing_toward(target)

    def test_facing_left_target_left(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="left")
        target = Position(4 * Settings.TILE_SIZE, 5 * Settings.TILE_SIZE)
        assert npc.is_facing_toward(target)

    def test_facing_right_target_right(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="right")
        target = Position(6 * Settings.TILE_SIZE, 5 * Settings.TILE_SIZE)
        assert npc.is_facing_toward(target)

    def test_facing_right_target_left(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="right")
        target = Position(4 * Settings.TILE_SIZE, 5 * Settings.TILE_SIZE)
        assert not npc.is_facing_toward(target)

    def test_same_position_returns_false(self):
        npc = make_npc(tile_x=5, tile_y=5, default_facing="down")
        target = Position(5 * Settings.TILE_SIZE, 5 * Settings.TILE_SIZE)
        assert not npc.is_facing_toward(target)


# ── _direction_toward ─────────────────────────────────────────

class TestDirectionToward:
    def test_player_below_npc(self):
        assert _direction_toward(0, 0, Position(0, 10)) == Direction.DOWN

    def test_player_above_npc(self):
        assert _direction_toward(0, 10, Position(0, 0)) == Direction.UP

    def test_player_right_of_npc(self):
        assert _direction_toward(0, 0, Position(10, 0)) == Direction.RIGHT

    def test_player_left_of_npc(self):
        assert _direction_toward(10, 0, Position(0, 0)) == Direction.LEFT

    def test_vertical_wins_on_equal(self):
        # dy == dx → vertical wins (abs(dy) >= abs(dx))
        assert _direction_toward(0, 0, Position(5, 5)) == Direction.DOWN

    def test_vertical_wins_when_dominant(self):
        assert _direction_toward(0, 0, Position(2, 10)) == Direction.DOWN


# ── default_facing ────────────────────────────────────────────

class TestDefaultFacing:
    def test_default_facing_down(self):
        npc = make_npc(default_facing="down")
        assert npc._default_facing == Direction.DOWN

    def test_default_facing_up(self):
        npc = make_npc(default_facing="up")
        assert npc._default_facing == Direction.UP

    def test_default_facing_left(self):
        npc = make_npc(default_facing="left")
        assert npc._default_facing == Direction.LEFT

    def test_default_facing_right(self):
        npc = make_npc(default_facing="right")
        assert npc._default_facing == Direction.RIGHT

    def test_unknown_facing_defaults_to_down(self):
        npc = make_npc(default_facing="north")
        assert npc._default_facing == Direction.DOWN


# ── _facing ───────────────────────────────────────────────────

class TestFacing:
    def test_not_near_returns_default(self):
        npc = make_npc(default_facing="up")
        player = Position(999, 999)
        assert npc._facing(player, near=False) == Direction.UP

    def test_near_faces_player_below(self):
        npc = make_npc(tile_x=5, tile_y=5)
        npc_py = 5 * Settings.TILE_SIZE
        player = Position(5 * Settings.TILE_SIZE, npc_py + 20)
        assert npc._facing(player, near=True) == Direction.DOWN

    def test_near_faces_player_above(self):
        npc = make_npc(tile_x=5, tile_y=5)
        npc_py = 5 * Settings.TILE_SIZE
        player = Position(5 * Settings.TILE_SIZE, npc_py - 20)
        assert npc._facing(player, near=True) == Direction.UP

    def test_near_no_player_pos_returns_default(self):
        npc = make_npc(default_facing="left")
        assert npc._facing(None, near=True) == Direction.LEFT
