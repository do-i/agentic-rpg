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

    # (firstgid, name) for each referenced tileset, ascending by firstgid so a
    # gid maps to the highest firstgid that does not exceed it.
    tilesets = sorted(
        (int(ts.get("firstgid")), Path(ts.get("source", "")).stem)
        for ts in root.findall("tileset")
    )
    if not any(name == tileset_name for _, name in tilesets):
        return []

    def resolve_local(gid: int) -> int | None:
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

    found: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for layer in root.findall("layer"):
        data = layer.find("data")
        if data is None or data.get("encoding") != "csv" or not data.text:
            continue
        cells = data.text.replace("\n", "").split(",")
        for index, raw in enumerate(cells):
            raw = raw.strip()
            if not raw:
                continue
            local = resolve_local(int(raw))
            if local is None or local not in tile_ids:
                continue
            coord = (index % width, index // width)
            if coord not in seen:
                seen.add(coord)
                found.append(coord)
    return found
