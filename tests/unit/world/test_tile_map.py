# tests/unit/world/test_tile_map.py

from __future__ import annotations

import pygame
import pytest
import pytmx
from unittest.mock import MagicMock, patch

from engine.world.tile_map import (
    TileMap, _load_enemy_spawn_tiles, _load_boss_spawn_tile,
    SPAWN_TILE_LAYER, BOSS_ENEMY_LAYER,
)

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


# ── _load_enemy_spawn_tiles ───────────────────────────────────

def _make_spawn_tile_layer(name: str, gid_grid: list[tuple[int, int, int]]) -> pytmx.TiledTileLayer:
    """Returns a TiledTileLayer whose `__iter__` yields (x, y, gid) tuples."""
    layer = MagicMock(spec=pytmx.TiledTileLayer)
    layer.name = name
    layer.__iter__ = lambda self: iter(gid_grid)
    return layer


class TestLoadEnemySpawnTiles:
    def test_returns_pixel_coords_for_each_gid(self):
        layer = _make_spawn_tile_layer(SPAWN_TILE_LAYER, [
            (0, 0, 1), (3, 2, 7), (5, 4, 0),  # gid=0 is empty
        ])
        tmx = _make_tmx(8, 8, [], all_layers=[layer])
        spawns = _load_enemy_spawn_tiles(tmx)
        assert spawns == [
            {"x": 0,        "y": 0},
            {"x": 3 * TW,   "y": 2 * TH},
        ]

    def test_returns_empty_when_no_spawn_layer(self):
        layer = _make_spawn_tile_layer("other_layer", [(0, 0, 1)])
        tmx = _make_tmx(4, 4, [], all_layers=[layer])
        assert _load_enemy_spawn_tiles(tmx) == []

    def test_returns_empty_when_layer_present_but_empty(self):
        layer = _make_spawn_tile_layer(SPAWN_TILE_LAYER, [])
        tmx = _make_tmx(4, 4, [], all_layers=[layer])
        assert _load_enemy_spawn_tiles(tmx) == []

    def test_skips_object_groups_with_same_name(self):
        obj_layer = MagicMock(spec=pytmx.TiledObjectGroup)
        obj_layer.name = SPAWN_TILE_LAYER
        tmx = _make_tmx(4, 4, [], all_layers=[obj_layer])
        # No tile layer matched → empty
        assert _load_enemy_spawn_tiles(tmx) == []


# ── _load_boss_spawn_tile ─────────────────────────────────────

def _make_obj_group(name: str, objects: list) -> pytmx.TiledObjectGroup:
    grp = MagicMock(spec=pytmx.TiledObjectGroup)
    grp.name = name
    grp.__iter__ = lambda self: iter(objects)
    return grp


def _obj(x: float, y: float):
    o = MagicMock()
    o.x = x
    o.y = y
    return o


class TestLoadBossSpawnTile:
    def test_returns_first_obj_snapped_to_tile_grid(self):
        # x=66 with TW=32 → round(66/32)=2 → 64
        # y=80 with TH=32 → round(80/32)=2.5 → banker's rounding → 96 actually round(2.5)=2 in py3
        grp = _make_obj_group(BOSS_ENEMY_LAYER, [_obj(66.0, 80.0)])
        tmx = _make_tmx(4, 4, [], all_layers=[grp])
        spawn = _load_boss_spawn_tile(tmx)
        assert spawn["is_boss"] is True
        # 66/32 = 2.0625 → round → 2 → 64
        assert spawn["x"] == 64
        # 80/32 = 2.5 → banker's rounds to 2 → 64
        assert spawn["y"] == 64

    def test_uses_only_first_object(self):
        grp = _make_obj_group(BOSS_ENEMY_LAYER, [_obj(0, 0), _obj(64, 64)])
        tmx = _make_tmx(4, 4, [], all_layers=[grp])
        spawn = _load_boss_spawn_tile(tmx)
        assert spawn == {"x": 0, "y": 0, "is_boss": True}

    def test_returns_none_when_layer_missing(self):
        tmx = _make_tmx(4, 4, [], all_layers=[])
        assert _load_boss_spawn_tile(tmx) is None

    def test_returns_none_when_layer_empty(self):
        grp = _make_obj_group(BOSS_ENEMY_LAYER, [])
        tmx = _make_tmx(4, 4, [], all_layers=[grp])
        assert _load_boss_spawn_tile(tmx) is None

    def test_skips_tile_layers_with_matching_name(self):
        layer = _make_spawn_tile_layer(BOSS_ENEMY_LAYER, [(0, 0, 1)])
        tmx = _make_tmx(4, 4, [], all_layers=[layer])
        assert _load_boss_spawn_tile(tmx) is None
