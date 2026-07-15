# tests/unit/tools/map_editor/test_web_server.py

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from tools.map_editor.web.server import create_app  # noqa: E402


@pytest.fixture
def client(scenario_root) -> TestClient:
    return TestClient(create_app(scenario_root))


class TestGraphEndpoint:
    def test_returns_nodes_and_edges(self, client):
        res = client.get("/api/graph")
        assert res.status_code == 200
        body = res.json()
        assert sorted(n["map_id"] for n in body["nodes"]) == ["town", "town_house"]
        assert len(body["edges"]) == 1


class TestRenderEndpoints:
    def test_thumbnail_png(self, client):
        res = client.get("/api/maps/town/thumbnail.png")
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/png"
        assert res.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_full_png(self, client):
        res = client.get("/api/maps/town/full.png")
        assert res.status_code == 200
        assert res.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_unknown_map_is_404(self, client):
        res = client.get("/api/maps/nowhere/thumbnail.png")
        assert res.status_code == 404


class TestPortalMutations:
    def test_create_returns_201_with_edge(self, client):
        res = client.post(
            "/api/portals",
            json={
                "source_map": "town_house",
                "source_rect_px": [16, 16, 16, 16],
                "target_map": "town",
                "target_tile": [2, 4],
            },
        )
        assert res.status_code == 201
        edge = res.json()
        assert edge["source"] == "town_house"
        assert edge["target"] == "town"
        assert edge["portal_obj_id"] > 0

    def test_create_unknown_target_is_404(self, client):
        res = client.post(
            "/api/portals",
            json={
                "source_map": "town",
                "source_rect_px": [0, 0, 16, 16],
                "target_map": "nowhere",
                "target_tile": [0, 0],
            },
        )
        assert res.status_code == 404

    def test_patch_retargets(self, client):
        res = client.patch(
            "/api/portals/town/1",
            json={
                "target_map": "town_house",
                "target_tile": [5, 5],
                "source_rect_px": None,
            },
        )
        assert res.status_code == 200
        assert res.json()["target_tile"] == [5, 5]

    def test_patch_unknown_portal_is_404(self, client):
        res = client.patch(
            "/api/portals/town/99",
            json={
                "target_map": "town_house",
                "target_tile": [5, 5],
                "source_rect_px": None,
            },
        )
        assert res.status_code == 404

    def test_delete_removes_edge(self, client):
        res = client.delete("/api/portals/town/1")
        assert res.status_code == 204
        assert client.get("/api/graph").json()["edges"] == []

    def test_delete_unknown_portal_is_404(self, client):
        res = client.delete("/api/portals/town/42")
        assert res.status_code == 404
