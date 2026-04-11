# tests/unit/world/test_portal_loader.py

import pytest
from unittest.mock import MagicMock
import pytmx

from engine.world.portal_loader import PortalLoader
from engine.common.portal_data import Portal
from engine.common.position_data import Position


def make_tmx(objects: list[dict]) -> pytmx.TiledMap:
    """Build a fake TiledMap with one portals object layer."""
    layer = MagicMock(spec=pytmx.TiledObjectGroup)
    layer.name = "portals"

    mock_objects = []
    for o in objects:
        obj = MagicMock()
        obj.x = o.get("x", 0)
        obj.y = o.get("y", 0)
        obj.width = o.get("width", 0)
        obj.height = o.get("height", 0)
        obj.properties = o.get("properties", {})
        mock_objects.append(obj)

    layer.__iter__ = MagicMock(return_value=iter(mock_objects))

    tmx = MagicMock(spec=pytmx.TiledMap)
    tmx.layers = [layer]
    return tmx


def make_empty_tmx() -> pytmx.TiledMap:
    tmx = MagicMock(spec=pytmx.TiledMap)
    tmx.layers = []
    return tmx


@pytest.fixture
def loader():
    return PortalLoader()


# ── load ──────────────────────────────────────────────────────

class TestPortalLoader:
    def test_empty_map_returns_empty(self, loader):
        assert loader.load(make_empty_tmx()) == []

    def test_loads_single_portal(self, loader):
        tmx = make_tmx([{
            "x": 448, "y": 608, "width": 32, "height": 32,
            "properties": {
                "target_map": "world_01",
                "target_position_x": 14,
                "target_position_y": 8,
            }
        }])
        portals = loader.load(tmx)
        assert len(portals) == 1
        assert portals[0].target_map == "world_01"
        assert portals[0].target_position == Position(14, 8)

    def test_loads_multiple_portals(self, loader):
        tmx = make_tmx([
            {"x": 100, "y": 200, "properties": {
                "target_map": "world_01",
                "target_position_x": 5, "target_position_y": 5,
            }},
            {"x": 300, "y": 400, "properties": {
                "target_map": "inn_01",
                "target_position_x": 3, "target_position_y": 2,
            }},
        ])
        portals = loader.load(tmx)
        assert len(portals) == 2

    def test_skips_object_missing_target_map(self, loader):
        tmx = make_tmx([{
            "x": 100, "y": 200,
            "properties": {"target_position_x": 5, "target_position_y": 5}
        }])
        assert loader.load(tmx) == []

    def test_skips_object_missing_position(self, loader):
        tmx = make_tmx([{
            "x": 100, "y": 200,
            "properties": {"target_map": "world_01"}
        }])
        assert loader.load(tmx) == []

    def test_point_object_has_zero_size(self, loader):
        tmx = make_tmx([{
            "x": 100, "y": 200, "width": 0, "height": 0,
            "properties": {
                "target_map": "world_01",
                "target_position_x": 5, "target_position_y": 5,
            }
        }])
        portal = loader.load(tmx)[0]
        assert portal.width == 0
        assert portal.height == 0

    def test_non_portal_layer_ignored(self, loader):
        layer = MagicMock(spec=pytmx.TiledObjectGroup)
        layer.name = "triggers"
        tmx = MagicMock(spec=pytmx.TiledMap)
        tmx.layers = [layer]
        assert loader.load(tmx) == []

    def test_tile_layer_ignored(self, loader):
        layer = MagicMock(spec=pytmx.TiledTileLayer)
        layer.name = "portals"
        tmx = MagicMock(spec=pytmx.TiledMap)
        tmx.layers = [layer]
        assert loader.load(tmx) == []
