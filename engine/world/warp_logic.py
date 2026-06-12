# engine/world/warp_logic.py
#
# Teleport / warp destination resolution for Aric's Teleport skill.
#
# A warp destination is a visited, top-level overworld map (town or area —
# not an interior such as a shop or inn). The landing tile for a destination
# is taken from an *existing incoming portal*: whichever portal elsewhere in
# the scenario leads into that map. This way teleporting drops the party at
# the same spot they would arrive at by walking through the door.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from engine.io.yaml_loader import load_yaml_optional_cached
from engine.world.position_data import Position


@dataclass(frozen=True)
class WarpDestination:
    map_id: str
    name: str
    position: Position


def _maps_assets_dir(scenario_path: Path) -> Path:
    return scenario_path / "assets" / "maps"


def _maps_data_dir(scenario_path: Path) -> Path:
    return scenario_path / "data" / "maps"


def _parse_portals(tmx_path: Path) -> list[tuple[str, Position]]:
    """Read the 'portals' object layer straight from the TMX XML.

    Parsing the XML directly (instead of via pytmx) avoids loading every
    tileset image just to read portal targets — important when scanning the
    whole scenario to build the landing index.
    """
    root = ET.parse(tmx_path).getroot()
    out: list[tuple[str, Position]] = []
    for group in root.iter("objectgroup"):
        if group.get("name") != "portals":
            continue
        for obj in group.findall("object"):
            props = {
                p.get("name"): p.get("value")
                for p in obj.findall("properties/property")
            }
            target_map = props.get("target_map")
            tx = props.get("target_position_x")
            ty = props.get("target_position_y")
            if not target_map or tx is None or ty is None:
                continue
            out.append((target_map, Position(int(tx), int(ty))))
    return out


def _is_submap(map_id: str, all_ids: set[str]) -> bool:
    """True when map_id is a sub-area of another map (e.g. an interior).

    Interiors and multi-segment areas are named by extending their parent's
    id with an underscore suffix — `town_01_ardel_shop_01` under
    `town_01_ardel`. We treat any such map as not a standalone warp target.
    """
    return any(
        other != map_id and map_id.startswith(other + "_")
        for other in all_ids
    )


def build_landing_index(maps_assets_dir: Path) -> dict[str, Position]:
    """Map each destination id to the tile a teleport should land on.

    Built from every incoming portal in the scenario. When a map has several
    incoming portals, prefer a source that is NOT one of its own sub-maps, so
    a town lands at its overworld entrance rather than at the tile in front of
    one of its shops. Ties broken by source id for determinism.
    """
    candidates: dict[str, list[tuple[bool, str, Position]]] = {}
    for tmx in sorted(maps_assets_dir.glob("*.tmx")):
        source_id = tmx.stem
        for target_map, position in _parse_portals(tmx):
            is_sub = source_id.startswith(target_map + "_")
            candidates.setdefault(target_map, []).append(
                (is_sub, source_id, position)
            )

    index: dict[str, Position] = {}
    for dest, cands in candidates.items():
        cands.sort(key=lambda c: (c[0], c[1]))
        index[dest] = cands[0][2]
    return index


def _load_map_name(maps_data_dir: Path, map_id: str) -> str:
    data = load_yaml_optional_cached(maps_data_dir / f"{map_id}.yaml")
    if not data:
        return map_id
    return data.get("name") or map_id


def warp_destinations(map_state, scenario_path: Path) -> list[WarpDestination]:
    """Visited, top-level locations Aric can teleport to, sorted by name.

    Excludes the current map, interiors/sub-maps, and any map with no known
    incoming portal (nowhere defined to land).
    """
    maps_assets = _maps_assets_dir(scenario_path)
    maps_data = _maps_data_dir(scenario_path)
    all_ids = {p.stem for p in maps_assets.glob("*.tmx")}
    landing = build_landing_index(maps_assets)

    out: list[WarpDestination] = []
    for map_id in map_state.visited:
        if map_id == map_state.current:
            continue
        if _is_submap(map_id, all_ids):
            continue
        if map_id not in landing:
            continue
        out.append(WarpDestination(
            map_id=map_id,
            name=_load_map_name(maps_data, map_id),
            position=landing[map_id],
        ))
    out.sort(key=lambda d: d.name)
    return out
