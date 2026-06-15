from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from engine.world.position_data import Position
from engine.world.sign import Sign
from engine.world.sign_locator import find_sign_tiles
from engine.world.sprite_sheet import Direction
from engine.world.world_map_logic import try_interact_sign

TSX = "stone_tile_stares_16x16"

# Minimal 4x3 map: tileset A at firstgid 1, the sign tileset at firstgid 337.
# Local id 19 of the sign tileset -> gid 356 (a sign); local id 4 -> gid 341
# (same tileset, not a sign); gid 1 belongs to the other tileset.
def _tmx(tmp_path, layers: list[list[int]]):
    layer_xml = "".join(
        f'<layer id="{i + 1}" name="L{i}" width="4" height="3">'
        f'<data encoding="csv">{",".join(str(v) for v in cells)}</data></layer>'
        for i, cells in enumerate(layers)
    )
    text = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<map version="1.10" width="4" height="3" tilewidth="32" tileheight="32">'
        '<tileset firstgid="1" source="../tilesets/other.tsx"/>'
        f'<tileset firstgid="337" source="../tilesets/{TSX}.tsx"/>'
        f"{layer_xml}</map>"
    )
    path = tmp_path / "m.tmx"
    path.write_text(text)
    return path


def test_find_sign_tiles_returns_coords_of_matching_tiles(tmp_path):
    #          idx: 0  1  2  3 / 4  5    6   7 / 8 9 10 11
    cells = [0, 1, 0, 0, 0, 341, 356, 0, 0, 0, 0, 0]
    path = _tmx(tmp_path, [cells])
    assert find_sign_tiles(path, TSX, {18, 19, 20, 21}) == [(2, 1)]


def test_find_sign_tiles_ignores_non_sign_local_ids(tmp_path):
    cells = [0, 0, 0, 0, 0, 341, 0, 0, 0, 0, 0, 0]  # only local id 4 present
    path = _tmx(tmp_path, [cells])
    assert find_sign_tiles(path, TSX, {18, 19, 20, 21}) == []


def test_find_sign_tiles_returns_empty_for_unknown_tileset(tmp_path):
    cells = [0, 0, 0, 0, 0, 0, 356, 0, 0, 0, 0, 0]
    path = _tmx(tmp_path, [cells])
    assert find_sign_tiles(path, "no_such_tileset", {19}) == []


def test_find_sign_tiles_dedupes_across_layers(tmp_path):
    cells = [0, 0, 0, 0, 0, 0, 356, 0, 0, 0, 0, 0]
    path = _tmx(tmp_path, [cells, list(cells)])  # same sign on two layers
    assert find_sign_tiles(path, TSX, {19}) == [(2, 1)]


def test_sign_is_near_within_interaction_range():
    sign = Sign("s", "sign_map", tile_x=2, tile_y=1, tile_size=32)  # px (64, 32)
    assert sign.is_near(Position(32, 32)) is True   # one tile left
    assert sign.is_near(Position(160, 32)) is False  # three tiles away


def _player(px, py, facing):
    return SimpleNamespace(
        pixel_position=Position(px, py),
        facing_direction=facing,
    )


def test_try_interact_sign_reads_faced_sign():
    sign = Sign("s", "sign_map", tile_x=2, tile_y=1, tile_size=32)  # px (64, 32)
    engine = MagicMock()
    engine.resolve.return_value = "RESULT"
    player = _player(32, 32, Direction.RIGHT)  # adjacent, facing the sign

    result = try_interact_sign(player, [sign], flags=MagicMock(), dialogue_engine=engine)

    assert result == "RESULT"
    engine.resolve.assert_called_once_with("sign_map", engine.resolve.call_args.args[1])


def test_try_interact_sign_ignores_sign_when_not_facing_it():
    sign = Sign("s", "sign_map", tile_x=2, tile_y=1, tile_size=32)
    engine = MagicMock()
    player = _player(32, 32, Direction.LEFT)  # adjacent but facing away

    assert try_interact_sign(player, [sign], flags=MagicMock(), dialogue_engine=engine) is None
    engine.resolve.assert_not_called()
