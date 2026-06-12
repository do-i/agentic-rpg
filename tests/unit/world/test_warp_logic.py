# tests/unit/world/test_warp_logic.py

from __future__ import annotations

from engine.common.map_state import MapState
from engine.world.position_data import Position
from engine.world.warp_logic import build_landing_index, warp_destinations


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

    (maps_data / "zone_forest.yaml").write_text("name: Greenwood Forest\n")
    (maps_data / "town_ardel.yaml").write_text("name: Ardel Village\n")
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
