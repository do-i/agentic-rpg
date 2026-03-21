# tests/unit/world/test_npc.py

import pytest
from engine.world.npc import Npc, INTERACTION_RANGE
from engine.core.state.flag_state import FlagState
from engine.core.models.position import Position
from engine.core.settings import Settings


def make_npc(
    tile_x=5, tile_y=5,
    requires=None, excludes=None,
) -> Npc:
    return Npc(
        npc_id="test_npc",
        dialogue_id="test_dialogue",
        tile_x=tile_x,
        tile_y=tile_y,
        present_requires=requires or [],
        present_excludes=excludes or [],
    )


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
