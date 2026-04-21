# tests/unit/world/test_world_map_item_box_integration.py
#
# Light integration between world_map_logic helpers, ItemBox,
# OpenedBoxesState, and RepositoryState.

from types import SimpleNamespace

from engine.common.flag_state import FlagState
from engine.common.opened_boxes_state import OpenedBoxesState
from engine.party.repository_state import RepositoryState
from engine.world.item_box import ItemBox
from engine.world.position_data import Position
from engine.world.sprite_sheet import Direction
from engine.world.world_map_logic import apply_item_box_loot, try_interact_item_box

TS = 32


def _player_at(tile_x: int, tile_y: int, facing: Direction = Direction.DOWN):
    """Minimal stand-in for Player used by try_interact_item_box."""
    return SimpleNamespace(
        pixel_position=Position(tile_x * TS, tile_y * TS),
        facing_direction=facing,
    )


def _box(box_id="c", tile_x=5, tile_y=6, items=None, mcs=None) -> ItemBox:
    return ItemBox(
        box_id=box_id,
        tile_x=tile_x,
        tile_y=tile_y,
        loot_items=items if items is not None else [("potion", 2)],
        loot_magic_cores=mcs if mcs is not None else [("mc_m", 1)],
        tile_size=TS,
    )


class TestTryInteract:
    def test_finds_facing_box(self):
        player = _player_at(5, 5, Direction.DOWN)
        box = _box(tile_x=5, tile_y=6)
        got = try_interact_item_box(player, [box], FlagState(), OpenedBoxesState(), "m")
        assert got is box

    def test_skips_already_opened(self):
        player = _player_at(5, 5, Direction.DOWN)
        box = _box(tile_x=5, tile_y=6)
        opened = OpenedBoxesState()
        opened.mark_opened("m", box.id)
        assert try_interact_item_box(player, [box], FlagState(), opened, "m") is None

    def test_skips_not_present(self):
        player = _player_at(5, 5, Direction.DOWN)
        box = ItemBox(
            box_id="c", tile_x=5, tile_y=6,
            loot_items=[], loot_magic_cores=[],
            tile_size=TS, present_requires=["never_set"],
        )
        assert try_interact_item_box(player, [box], FlagState(), OpenedBoxesState(), "m") is None

    def test_skips_not_facing(self):
        player = _player_at(5, 5, Direction.UP)  # facing away from box below
        box = _box(tile_x=5, tile_y=6)
        assert try_interact_item_box(player, [box], FlagState(), OpenedBoxesState(), "m") is None

    def test_picks_nearest(self):
        player = _player_at(5, 5, Direction.DOWN)
        near = _box(box_id="near", tile_x=5, tile_y=6)
        far  = _box(box_id="far",  tile_x=5, tile_y=7)
        got = try_interact_item_box(player, [far, near], FlagState(), OpenedBoxesState(), "m")
        assert got is near


class TestApplyLoot:
    def test_transfers_items_and_magic_cores(self):
        repo = RepositoryState()
        opened = OpenedBoxesState()
        box = _box(items=[("potion", 2), ("antidote", 1)], mcs=[("mc_m", 3), ("mc_s", 5)])
        apply_item_box_loot(box, repo, opened, "m")

        assert repo.get_item("potion").qty == 2
        assert repo.get_item("antidote").qty == 1
        assert repo.get_item("mc_m").qty == 3
        assert repo.get_item("mc_s").qty == 5
        assert opened.is_opened("m", box.id)

    def test_magic_core_entries_tagged(self):
        repo = RepositoryState()
        box = _box(items=[], mcs=[("mc_l", 1)])
        apply_item_box_loot(box, repo, OpenedBoxesState(), "m")
        assert "magic_core" in repo.get_item("mc_l").tags

    def test_second_interaction_is_noop(self):
        """After looting, the box becomes opened and try_interact rejects it."""
        player = _player_at(5, 5, Direction.DOWN)
        repo = RepositoryState()
        opened = OpenedBoxesState()
        box = _box(tile_x=5, tile_y=6)

        first = try_interact_item_box(player, [box], FlagState(), opened, "m")
        assert first is box
        apply_item_box_loot(first, repo, opened, "m")

        second = try_interact_item_box(player, [box], FlagState(), opened, "m")
        assert second is None
