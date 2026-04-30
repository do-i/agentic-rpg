# tests/unit/world/test_item_box.py

from __future__ import annotations

from engine.common.flag_state import FlagState
from engine.world.item_box import ItemBox
from engine.world.position_data import Position

TS = 32


def make_box(
    tile_x=5, tile_y=5,
    requires=None, excludes=None,
    loot_items=None, loot_magic_cores=None,
) -> ItemBox:
    return ItemBox(
        box_id="test_box",
        tile_x=tile_x,
        tile_y=tile_y,
        loot_items=loot_items if loot_items is not None else [("potion", 1)],
        loot_magic_cores=loot_magic_cores if loot_magic_cores is not None else [],
        tile_size=TS,
        present_requires=requires or [],
        present_excludes=excludes or [],
        sprite=None,
    )


class TestIsPresent:
    def test_no_conditions_always_present(self):
        assert make_box().is_present(FlagState())

    def test_requires_met(self):
        box = make_box(requires=["flag_a"])
        assert box.is_present(FlagState({"flag_a"}))

    def test_requires_not_met(self):
        box = make_box(requires=["flag_a"])
        assert not box.is_present(FlagState())

    def test_excludes_blocks(self):
        box = make_box(excludes=["flag_a"])
        assert not box.is_present(FlagState({"flag_a"}))


class TestCollisionRect:
    def test_full_tile_footprint(self):
        box = make_box(tile_x=5, tile_y=7)
        assert box.collision_rect == (5 * TS, 7 * TS, TS, TS)


class TestIsNear:
    def test_same_position(self):
        box = make_box(tile_x=5, tile_y=5)
        assert box.is_near(Position(5 * TS, 5 * TS))

    def test_adjacent_tile(self):
        box = make_box(tile_x=5, tile_y=5)
        assert box.is_near(Position(6 * TS, 5 * TS))

    def test_far_position(self):
        box = make_box(tile_x=5, tile_y=5)
        assert not box.is_near(Position(20 * TS, 20 * TS))


class TestSortY:
    def test_sort_y_is_bottom_of_sprite(self):
        box = make_box(tile_x=4, tile_y=10)
        assert box.sort_y == 10 * TS + TS
