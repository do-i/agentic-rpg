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


CATEGORY_TOWN = "town"
CATEGORY_WORLD = "world"


@dataclass(frozen=True)
class WarpDestination:
    map_id: str
    name: str
    position: Position
    category: str  # CATEGORY_TOWN | CATEGORY_WORLD
    order: int     # warp_order from the map yaml (low = earlier in the list)


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


def _load_map_data(maps_data_dir: Path, map_id: str) -> dict:
    return load_yaml_optional_cached(maps_data_dir / f"{map_id}.yaml") or {}


def _map_name(data: dict, map_id: str) -> str:
    return data.get("name") or map_id


def _map_category(data: dict) -> str:
    """Classify a destination as a town or a world-map zone.

    Read from the scenario data rather than hardcoded id prefixes: settlements
    carry an ``inn`` and/or ``shop`` block, while overworld field zones do not.
    """
    if "inn" in data or "shop" in data:
        return CATEGORY_TOWN
    return CATEGORY_WORLD


def _map_order(data: dict, maps_data_dir: Path, map_id: str) -> int:
    """The ``warp_order`` declared by a teleport-target map.

    Required (no default): the teleport list ordering is data-driven, so a
    warp-reachable map with no ``warp_order`` is a scenario error we surface
    rather than guess a position for.
    """
    order = data.get("warp_order")
    if order is None:
        raise ValueError(
            f"warp destination {map_id!r} is missing required property "
            f"'warp_order' in {maps_data_dir / f'{map_id}.yaml'}.\n"
            f"Add an integer ordering it within its group (towns / world map), "
            f"e.g.\n  warp_order: 40"
        )
    return int(order)


def warp_destinations(map_state, scenario_path: Path) -> list[WarpDestination]:
    """Visited, top-level locations Aric can teleport to.

    Grouped by category — towns first, then world-map zones — and within each
    group ordered by each map's ``warp_order`` (a predefined natural/progression
    order declared in the map yaml). Excludes the current map, interiors/
    sub-maps, and any map with no known incoming portal (nowhere to land).
    """
    maps_assets = _maps_assets_dir(scenario_path)
    maps_data = _maps_data_dir(scenario_path)
    all_ids = {p.stem for p in maps_assets.glob("*.tmx")}
    landing = build_landing_index(maps_assets)

    towns: list[WarpDestination] = []
    world: list[WarpDestination] = []
    for map_id in map_state.visited:
        if map_id == map_state.current:
            continue
        if _is_submap(map_id, all_ids):
            continue
        if map_id not in landing:
            continue
        data = _load_map_data(maps_data, map_id)
        category = _map_category(data)
        dest = WarpDestination(
            map_id=map_id,
            name=_map_name(data, map_id),
            position=landing[map_id],
            category=category,
            order=_map_order(data, maps_data, map_id),
        )
        (towns if category == CATEGORY_TOWN else world).append(dest)

    towns.sort(key=lambda d: d.order)
    world.sort(key=lambda d: d.order)
    return towns + world
