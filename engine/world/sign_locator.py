# engine/world/sign_locator.py
#
# Finds "message board" sign tiles inside a TMX map by reading the raw XML.
#
# Sign tiles are ordinary map tiles (specific local ids of a named tileset)
# that the scenario author has painted onto a layer. We resolve them straight
# from the .tmx CSV rather than through pytmx because pytmx remaps global tile
# ids at load time, which makes "local id N of tileset X" impossible to recover
# reliably from the loaded object. The raw firstgid ranges in the file are the
# source of truth.

from __future__ import annotations

from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

# Tiled stores horizontal/vertical/diagonal flip state in the top three bits of
# each gid. Mask them off before comparing against tileset firstgid ranges.
_GID_FLAGS_MASK = 0x1FFFFFFF


def find_sign_tiles(
    tmx_path: Path,
    tileset_name: str,
    tile_ids: set[int],
) -> list[tuple[int, int]]:
    """Return (tile_x, tile_y) of every sign tile painted in *tmx_path*.

    A cell counts as a sign when its gid resolves to *tileset_name* with a
    local id in *tile_ids*. Scans every tile layer; the same coordinate is
    only reported once even if several layers stack a sign there.
    """
    if not tmx_path.exists():
        return []

    root = ET.parse(tmx_path).getroot()
    width = int(root.get("width"))
    tilesets = _referenced_tilesets(root)
    if not any(name == tileset_name for _, name in tilesets):
        return []

    found: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for layer in root.findall("layer"):
        for coord, local in _iter_layer_tiles(layer, width, tilesets, tileset_name):
            if local in tile_ids and coord not in seen:
                seen.add(coord)
                found.append(coord)
    return found


def _referenced_tilesets(root: ET.Element) -> list[tuple[int, str]]:
    """(firstgid, name) for each referenced tileset, ascending by firstgid so
    a gid maps to the highest firstgid that does not exceed it."""
    return sorted(
        (int(ts.get("firstgid")), Path(ts.get("source", "")).stem)
        for ts in root.findall("tileset")
    )


def _local_tile_id(
    gid: int, tilesets: list[tuple[int, str]], tileset_name: str,
) -> int | None:
    """Local id of *gid* within *tileset_name*, or None if it belongs to a
    different tileset (or is the empty cell)."""
    real = gid & _GID_FLAGS_MASK
    if real == 0:
        return None
    match = None
    for first, name in tilesets:
        if first <= real:
            match = (first, name)
        else:
            break
    if match is None or match[1] != tileset_name:
        return None
    return real - match[0]


def _iter_layer_tiles(
    layer: ET.Element,
    width: int,
    tilesets: list[tuple[int, str]],
    tileset_name: str,
) -> Iterator[tuple[tuple[int, int], int]]:
    """Yield ((tile_x, tile_y), local_id) for each cell of *layer* whose gid
    resolves to *tileset_name*. Skips non-CSV layers."""
    data = layer.find("data")
    if data is None or data.get("encoding") != "csv" or not data.text:
        return
    cells = data.text.replace("\n", "").split(",")
    for index, raw in enumerate(cells):
        raw = raw.strip()
        if not raw:
            continue
        local = _local_tile_id(int(raw), tilesets, tileset_name)
        if local is None:
            continue
        yield (index % width, index // width), local
