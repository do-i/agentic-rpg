# tests/unit/world/test_tile_map.py

import pygame
import pytest
import pytmx
from unittest.mock import MagicMock, patch

from engine.world.tile_map import TileMap

TW = 32
TH = 32


def _make_tile_layer(name: str, tiles: list[tuple[int, int, pygame.Surface]]) -> pytmx.TiledTileLayer:
    """A TiledTileLayer mock whose .tiles() returns the given (x, y, image) tuples."""
    layer = MagicMock(spec=pytmx.TiledTileLayer)
    layer.name = name
    layer.tiles.return_value = list(tiles)
    layer.__iter__ = MagicMock(return_value=iter([]))  # for collision/spawn iteration
    return layer


def _make_tmx(
    width_tiles: int,
    height_tiles: int,
    visible_layers: list,
    all_layers: list | None = None,
) -> pytmx.TiledMap:
    tmx = MagicMock(spec=pytmx.TiledMap)
    tmx.tilewidth = TW
    tmx.tileheight = TH
    tmx.width = width_tiles
    tmx.height = height_tiles
    tmx.visible_layers = visible_layers
    tmx.layers = all_layers if all_layers is not None else visible_layers
    return tmx


@pytest.fixture(autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def _solid_tile(color: tuple[int, int, int, int]) -> pygame.Surface:
    surf = pygame.Surface((TW, TH), pygame.SRCALPHA)
    surf.fill(color)
    return surf


class TestPrerenderLayers:
    def test_single_layer_painted_at_tile_positions(self):
        red = _solid_tile((255, 0, 0, 255))
        tile_layer = _make_tile_layer("ground", [(0, 0, red), (2, 1, red)])
        tmx = _make_tmx(4, 3, [tile_layer])

        with patch("pytmx.load_pygame", return_value=tmx):
            tile_map = TileMap("ignored.tmx", collision_factory=MagicMock(), portal_loader=MagicMock())

        assert len(tile_map._layer_surfaces) == 1
        surf = tile_map._layer_surfaces[0]
        assert surf.get_size() == (4 * TW, 3 * TH)
        # Painted tiles
        assert surf.get_at((0, 0)) == (255, 0, 0, 255)
        assert surf.get_at((2 * TW, 1 * TH)) == (255, 0, 0, 255)
        # Unpainted tiles remain transparent
        assert surf.get_at((1 * TW, 0)) == (0, 0, 0, 0)

    def test_skips_non_tile_layers(self):
        obj_layer = MagicMock(spec=pytmx.TiledObjectGroup)
        obj_layer.name = "portals"
        tile_layer = _make_tile_layer("ground", [(0, 0, _solid_tile((10, 20, 30, 255)))])
        tmx = _make_tmx(2, 2, [obj_layer, tile_layer])

        with patch("pytmx.load_pygame", return_value=tmx):
            tile_map = TileMap("ignored.tmx", collision_factory=MagicMock(), portal_loader=MagicMock())

        assert len(tile_map._layer_surfaces) == 1

    def test_multiple_layers_kept_in_order(self):
        a = _make_tile_layer("ground", [(0, 0, _solid_tile((1, 0, 0, 255)))])
        b = _make_tile_layer("decoration", [(0, 0, _solid_tile((0, 2, 0, 255)))])
        tmx = _make_tmx(1, 1, [a, b])

        with patch("pytmx.load_pygame", return_value=tmx):
            tile_map = TileMap("ignored.tmx", collision_factory=MagicMock(), portal_loader=MagicMock())

        assert len(tile_map._layer_surfaces) == 2
        # The second surface should be the green one.
        assert tile_map._layer_surfaces[1].get_at((0, 0)) == (0, 2, 0, 255)


class TestRender:
    def test_blits_each_layer_at_negative_offset(self):
        tile_layer = _make_tile_layer("ground", [(0, 0, _solid_tile((255, 0, 0, 255)))])
        tmx = _make_tmx(2, 2, [tile_layer])

        with patch("pytmx.load_pygame", return_value=tmx):
            tile_map = TileMap("ignored.tmx", collision_factory=MagicMock(), portal_loader=MagicMock())

        screen = pygame.Surface((TW * 2, TH * 2), pygame.SRCALPHA)
        # Render with no offset — tile at (0,0) should be painted.
        tile_map.render(screen, 0, 0)
        assert screen.get_at((0, 0)) == (255, 0, 0, 255)

    def test_offset_shifts_layer(self):
        tile_layer = _make_tile_layer("ground", [(1, 0, _solid_tile((0, 0, 255, 255)))])
        tmx = _make_tmx(2, 1, [tile_layer])

        with patch("pytmx.load_pygame", return_value=tmx):
            tile_map = TileMap("ignored.tmx", collision_factory=MagicMock(), portal_loader=MagicMock())

        screen = pygame.Surface((TW * 2, TH), pygame.SRCALPHA)
        # Tile is at world x=TW. With offset_x=TW, it should land at screen x=0.
        tile_map.render(screen, TW, 0)
        assert screen.get_at((0, 0)) == (0, 0, 255, 255)

    def test_offscreen_blit_does_not_crash(self):
        tile_layer = _make_tile_layer("ground", [(0, 0, _solid_tile((255, 0, 0, 255)))])
        tmx = _make_tmx(1, 1, [tile_layer])

        with patch("pytmx.load_pygame", return_value=tmx):
            tile_map = TileMap("ignored.tmx", collision_factory=MagicMock(), portal_loader=MagicMock())

        screen = pygame.Surface((TW, TH), pygame.SRCALPHA)
        tile_map.render(screen, 1000, 1000)  # entire layer is off-screen
