# tests/unit/world/test_warp_logic.py

from __future__ import annotations

import pytest

from engine.common.map_state import MapState
from engine.world.position_data import Position
from engine.world.warp_logic import (
    CATEGORY_TOWN, CATEGORY_WORLD, build_landing_index, warp_destinations,
)


def _tmx(portals) -> str:
    objs = ""
    for i, (target_map, (tx, ty)) in enumerate(portals):
        objs += (
            f'<object id="{i + 1}" x="0" y="0" width="8" height="8"><properties>'
            f'<property name="target_map" value="{target_map}"/>'
            f'<property name="target_position_x" type="int" value="{tx}"/>'
            f'<property name="target_position_y" type="int" value="{ty}"/>'
            f'</properties></object>'
        )
    return f'<?xml version="1.0"?><map><objectgroup name="portals">{objs}</objectgroup></map>'


def _build_scenario(tmp_path):
    maps_assets = tmp_path / "assets" / "maps"
    maps_data = tmp_path / "data" / "maps"
    maps_assets.mkdir(parents=True)
    maps_data.mkdir(parents=True)

    (maps_assets / "zone_forest.tmx").write_text(_tmx([("town_ardel", (27, 12))]))
    (maps_assets / "town_ardel.tmx").write_text(
        _tmx([("zone_forest", (5, 5)), ("town_ardel_shop", (3, 3))]))
    (maps_assets / "town_ardel_shop.tmx").write_text(_tmx([("town_ardel", (9, 9))]))

    (maps_data / "zone_forest.yaml").write_text(
        "name: Greenwood Forest\nwarp_order: 20\n")
    (maps_data / "town_ardel.yaml").write_text(
        "name: Ardel Village\nwarp_order: 10\nshop:\n  items: []\n")
    (maps_data / "town_ardel_shop.yaml").write_text("name: Ardel Shop\n")
    return tmp_path


class TestLandingIndex:
    def test_prefers_overworld_entrance_over_interior_exit(self, tmp_path):
        _build_scenario(tmp_path)
        index = build_landing_index(tmp_path / "assets" / "maps")
        # town_ardel is targeted by zone_forest (entrance) and by its shop
        # (interior exit). The non-sub-map source wins.
        assert index["town_ardel"] == Position(27, 12)
        assert index["zone_forest"] == Position(5, 5)


class TestWarpDestinations:
    def test_lists_visited_top_level_maps_only(self, tmp_path):
        _build_scenario(tmp_path)
        state = MapState(current="zone_forest", position=Position(1, 1),
                         visited={"town_ardel", "town_ardel_shop"})
        dests = warp_destinations(state, tmp_path)
        # Shop interior is a sub-map → excluded; only the town remains.
        assert [d.map_id for d in dests] == ["town_ardel"]
        assert dests[0].name == "Ardel Village"
        assert dests[0].position == Position(27, 12)

    def test_excludes_current_map(self, tmp_path):
        _build_scenario(tmp_path)
        state = MapState(current="town_ardel", position=Position(1, 1),
                         visited={"town_ardel", "zone_forest"})
        dests = warp_destinations(state, tmp_path)
        assert [d.map_id for d in dests] == ["zone_forest"]

    def test_empty_when_nothing_visited(self, tmp_path):
        _build_scenario(tmp_path)
        state = MapState(current="zone_forest", position=Position(1, 1))
        assert warp_destinations(state, tmp_path) == []


def _build_grouped_scenario(tmp_path):
    """Two towns and two field zones, all top-level and mutually portalled."""
    maps_assets = tmp_path / "assets" / "maps"
    maps_data = tmp_path / "data" / "maps"
    maps_assets.mkdir(parents=True)
    maps_data.mkdir(parents=True)

    ids = ["town_one", "town_two", "zone_a", "zone_b"]
    for map_id in ids:
        # Every map has an incoming portal from "hub" so it gets a landing tile.
        (maps_assets / f"{map_id}.tmx").write_text(_tmx([("hub", (1, 1))]))
    (maps_assets / "hub.tmx").write_text(
        _tmx([(m, (i + 1, i + 1)) for i, m in enumerate(ids)]))

    # Towns carry a shop/inn block; field zones do not. warp_order is declared
    # out of alphabetical / visit order to prove the sort honors it.
    (maps_data / "town_one.yaml").write_text(
        "name: First Town\nwarp_order: 40\nshop:\n  items: []\n")
    (maps_data / "town_two.yaml").write_text(
        "name: Second Town\nwarp_order: 10\ninn:\n  cost: 10\n")
    (maps_data / "zone_a.yaml").write_text("name: Field A\nwarp_order: 30\n")
    (maps_data / "zone_b.yaml").write_text("name: Field B\nwarp_order: 20\n")
    return tmp_path


class TestWarpGroupingAndOrder:
    def test_groups_towns_before_world_and_sorts_by_warp_order(self, tmp_path):
        _build_grouped_scenario(tmp_path)
        # Visit order deliberately scrambled; ordering must come from warp_order.
        state = MapState(current="hub", position=Position(0, 0),
                         visited={"zone_b", "town_one", "zone_a", "town_two"})

        dests = warp_destinations(state, tmp_path)
        # Towns first (by warp_order: town_two=10 then town_one=40), then world
        # zones (zone_b=20 then zone_a=30).
        assert [d.map_id for d in dests] == [
            "town_two", "town_one", "zone_b", "zone_a",
        ]
        assert [d.category for d in dests] == [
            CATEGORY_TOWN, CATEGORY_TOWN, CATEGORY_WORLD, CATEGORY_WORLD,
        ]

    def test_missing_warp_order_raises(self, tmp_path):
        _build_grouped_scenario(tmp_path)
        (tmp_path / "data" / "maps" / "town_one.yaml").write_text(
            "name: First Town\nshop:\n  items: []\n")
        state = MapState(current="hub", position=Position(0, 0),
                         visited={"town_one"})
        with pytest.raises(ValueError, match="warp_order"):
            warp_destinations(state, tmp_path)
