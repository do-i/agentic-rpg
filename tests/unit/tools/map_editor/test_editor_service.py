# tests/unit/tools/map_editor/test_editor_service.py

from __future__ import annotations

import pytest

from tools.map_editor.service.editor_service import EditorService


@pytest.fixture
def service(scenario_root) -> EditorService:
    return EditorService(scenario_root)


class TestGraphDict:
    def test_lists_all_maps_as_nodes(self, service):
        graph = service.graph_dict()
        assert sorted(n["map_id"] for n in graph["nodes"]) == [
            "town",
            "town_house",
        ]

    def test_node_carries_yaml_metadata(self, service):
        graph = service.graph_dict()
        town = next(n for n in graph["nodes"] if n["map_id"] == "town")
        assert town["display_name"] == "Town"
        assert town["bgm"] == "town_theme"
        assert town["has_inn"] is True
        assert town["is_world"] is True
        assert town["map_size_px"] == [160, 128]
        assert town["tile_size_px"] == [16, 16]

    def test_interior_map_is_not_world(self, service):
        graph = service.graph_dict()
        house = next(n for n in graph["nodes"] if n["map_id"] == "town_house")
        assert house["is_world"] is False

    def test_edge_reflects_portal(self, service):
        graph = service.graph_dict()
        assert len(graph["edges"]) == 1
        edge = graph["edges"][0]
        assert edge["id"] == "town#1"
        assert edge["source"] == "town"
        assert edge["target"] == "town_house"
        assert edge["source_tile"] == [2, 3]
        assert edge["target_tile"] == [3, 4]
        assert edge["source_rect_px"] == [32, 48, 16, 16]


class TestCreatePortal:
    def test_returns_new_edge(self, service):
        edge = service.create_portal(
            source_map="town_house",
            source_rect_px=(16, 16, 16, 16),
            target_map="town",
            target_tile=(2, 4),
        )
        assert edge["source"] == "town_house"
        assert edge["target"] == "town"
        assert edge["target_tile"] == [2, 4]
        assert edge["portal_obj_id"] > 0

    def test_new_edge_appears_in_graph(self, service):
        service.create_portal(
            source_map="town_house",
            source_rect_px=(16, 16, 16, 16),
            target_map="town",
            target_tile=(2, 4),
        )
        graph = service.graph_dict()
        assert len(graph["edges"]) == 2

    def test_persists_across_reload(self, service, scenario_root):
        service.create_portal(
            source_map="town_house",
            source_rect_px=(16, 16, 16, 16),
            target_map="town",
            target_tile=(2, 4),
        )
        reloaded = EditorService(scenario_root)
        assert len(reloaded.graph_dict()["edges"]) == 2

    def test_writes_backup_on_first_edit(self, service, scenario_root):
        service.create_portal(
            source_map="town_house",
            source_rect_px=(16, 16, 16, 16),
            target_map="town",
            target_tile=(2, 4),
        )
        bak = scenario_root / "assets" / "maps" / "town_house.tmx.bak"
        assert bak.is_file()

    def test_unknown_source_map_raises(self, service):
        with pytest.raises(ValueError, match="Unknown map id 'nowhere'"):
            service.create_portal(
                source_map="nowhere",
                source_rect_px=(0, 0, 16, 16),
                target_map="town",
                target_tile=(0, 0),
            )

    def test_unknown_target_map_raises(self, service):
        with pytest.raises(ValueError, match="Unknown map id 'nowhere'"):
            service.create_portal(
                source_map="town",
                source_rect_px=(0, 0, 16, 16),
                target_map="nowhere",
                target_tile=(0, 0),
            )


class TestRetargetPortal:
    def test_updates_target(self, service):
        edge = service.retarget_portal(
            source_map="town",
            portal_obj_id=1,
            target_map="town_house",
            target_tile=(5, 5),
            source_rect_px=None,
        )
        assert edge["target_tile"] == [5, 5]

    def test_keeps_geometry_when_rect_none(self, service):
        edge = service.retarget_portal(
            source_map="town",
            portal_obj_id=1,
            target_map="town_house",
            target_tile=(5, 5),
            source_rect_px=None,
        )
        assert edge["source_rect_px"] == [32, 48, 16, 16]

    def test_moves_geometry_when_rect_given(self, service):
        edge = service.retarget_portal(
            source_map="town",
            portal_obj_id=1,
            target_map="town_house",
            target_tile=(5, 5),
            source_rect_px=(64, 64, 32, 16),
        )
        assert edge["source_rect_px"] == [64, 64, 32, 16]
        assert edge["source_tile"] == [4, 4]

    def test_persists_across_reload(self, service, scenario_root):
        service.retarget_portal(
            source_map="town",
            portal_obj_id=1,
            target_map="town_house",
            target_tile=(5, 5),
            source_rect_px=None,
        )
        reloaded = EditorService(scenario_root)
        assert reloaded.graph_dict()["edges"][0]["target_tile"] == [5, 5]

    def test_unknown_portal_raises(self, service):
        with pytest.raises(ValueError, match="No portal with object id 99"):
            service.retarget_portal(
                source_map="town",
                portal_obj_id=99,
                target_map="town_house",
                target_tile=(0, 0),
                source_rect_px=None,
            )


class TestDeletePortal:
    def test_removes_edge_from_graph(self, service):
        service.delete_portal(source_map="town", portal_obj_id=1)
        assert service.graph_dict()["edges"] == []

    def test_persists_across_reload(self, service, scenario_root):
        service.delete_portal(source_map="town", portal_obj_id=1)
        reloaded = EditorService(scenario_root)
        assert reloaded.graph_dict()["edges"] == []

    def test_unknown_portal_raises(self, service):
        with pytest.raises(ValueError, match="No portal with object id 42"):
            service.delete_portal(source_map="town", portal_obj_id=42)
