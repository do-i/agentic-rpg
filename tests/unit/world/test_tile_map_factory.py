# tests/unit/world/test_tile_map_factory.py

from __future__ import annotations

from unittest.mock import patch, MagicMock

from engine.world.tile_map_factory import TileMapFactory


class TestTileMapFactory:
    def test_create_returns_tile_map(self):
        factory = TileMapFactory()
        with patch("engine.world.tile_map.pytmx.load_pygame") as load:
            tmx = MagicMock()
            tmx.tilewidth = 32
            tmx.tileheight = 32
            tmx.width = 4
            tmx.height = 4
            tmx.layers = []
            tmx.visible_layers = []
            load.return_value = tmx

            tile_map = factory.create("ignored.tmx")

        assert tile_map.tile_width == 32
        assert tile_map.width_px == 4 * 32
        load.assert_called_once_with("ignored.tmx", pixelalpha=True)

    def test_factory_is_stateless(self):
        # Same factory can build multiple maps without leaking between them.
        factory = TileMapFactory()
        with patch("engine.world.tile_map.pytmx.load_pygame") as load:
            tmx_a = MagicMock(tilewidth=16, tileheight=16, width=2, height=2,
                              layers=[], visible_layers=[])
            tmx_b = MagicMock(tilewidth=64, tileheight=64, width=8, height=8,
                              layers=[], visible_layers=[])
            load.side_effect = [tmx_a, tmx_b]
            a = factory.create("a.tmx")
            b = factory.create("b.tmx")
        assert a.tile_width == 16
        assert b.tile_width == 64
