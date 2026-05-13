"""Build a node/edge graph of the scenario from portal connections.

Nodes are map ids (TMX file stems). Edges are directed portal links read
from the 'portals' object group in each TMX: one edge per portal, so two
portals between the same pair of maps produce two edges. Maps that fail
to parse are skipped, but still appear as nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytmx
import yaml


@dataclass(frozen=True)
class NpcMeta:
    npc_id: str
    name: str | None
    dialogue: str | None
    position: tuple[int, int] | None


@dataclass(frozen=True)
class ItemBoxMeta:
    box_id: str
    position: tuple[int, int] | None


@dataclass
class GraphNode:
    map_id: str
    tmx_path: Path
    yaml_path: Path | None
    display_name: str
    bgm: str | None
    has_inn: bool
    has_shop: bool
    has_apothecary: bool
    has_magic_core_shop: bool
    npcs: tuple[NpcMeta, ...]
    item_boxes: tuple[ItemBoxMeta, ...]
    encounter: dict | None
    map_size_px: tuple[int, int]    # full map pixel dimensions
    tile_size_px: tuple[int, int]   # individual tile pixel dimensions


@dataclass
class GraphEdge:
    source: str
    target: str
    source_tile: tuple[int, int]    # portal's top-left tile on the source map
    target_tile: tuple[int, int]    # destination tile on the target map


@dataclass
class PortalGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    nodes_by_id: dict[str, GraphNode] = field(default_factory=dict)


def build_portal_graph(
    tmx_paths: list[Path],
    yaml_for: callable,
) -> PortalGraph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for tmx_path in tmx_paths:
        map_id = tmx_path.stem
        yaml_path = yaml_for(tmx_path)
        meta = _read_yaml_meta(yaml_path) if yaml_path else _empty_meta()
        tmx_info = _read_tmx_info(tmx_path)
        nodes.append(
            GraphNode(
                map_id=map_id,
                tmx_path=tmx_path,
                yaml_path=yaml_path,
                display_name=meta["name"] or map_id,
                bgm=meta["bgm"],
                has_inn=meta["has_inn"],
                has_shop=meta["has_shop"],
                has_apothecary=meta["has_apothecary"],
                has_magic_core_shop=meta["has_magic_core_shop"],
                npcs=meta["npcs"],
                item_boxes=meta["item_boxes"],
                encounter=meta["encounter"],
                map_size_px=(tmx_info["map_w_px"], tmx_info["map_h_px"]),
                tile_size_px=(tmx_info["tile_w"], tmx_info["tile_h"]),
            )
        )
        tw = tmx_info["tile_w"] or 1
        th = tmx_info["tile_h"] or 1
        for record in tmx_info["portals"]:
            edges.append(
                GraphEdge(
                    source=map_id,
                    target=record["target_map"],
                    source_tile=(record["source_x"] // tw, record["source_y"] // th),
                    target_tile=(record["target_x"], record["target_y"]),
                )
            )

    nodes_by_id = {n.map_id: n for n in nodes}
    return PortalGraph(nodes=nodes, edges=edges, nodes_by_id=nodes_by_id)


def _empty_meta() -> dict:
    return {
        "name": None,
        "bgm": None,
        "has_inn": False,
        "has_shop": False,
        "has_apothecary": False,
        "has_magic_core_shop": False,
        "npcs": (),
        "item_boxes": (),
        "encounter": None,
    }


def _read_yaml_meta(yaml_path: Path) -> dict:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    npcs: list[NpcMeta] = []
    for entry in data.get("npcs") or []:
        if not isinstance(entry, dict):
            continue
        pos = entry.get("position")
        npcs.append(
            NpcMeta(
                npc_id=str(entry.get("id") or "?"),
                name=entry.get("name"),
                dialogue=entry.get("dialogue"),
                position=(int(pos[0]), int(pos[1])) if pos else None,
            )
        )

    boxes: list[ItemBoxMeta] = []
    for entry in data.get("item_boxes") or []:
        if not isinstance(entry, dict):
            continue
        pos = entry.get("position")
        boxes.append(
            ItemBoxMeta(
                box_id=str(entry.get("id") or "?"),
                position=(int(pos[0]), int(pos[1])) if pos else None,
            )
        )

    encounter = data.get("encounter") or data.get("enemy_spawn")

    return {
        "name": data.get("name"),
        "bgm": data.get("bgm"),
        "has_inn": "inn" in data,
        "has_shop": "shop" in data,
        "has_apothecary": "apothecary" in data,
        "has_magic_core_shop": "magic_core_shop" in data,
        "npcs": tuple(npcs),
        "item_boxes": tuple(boxes),
        "encounter": encounter if isinstance(encounter, dict) else None,
    }


def _read_tmx_info(tmx_path: Path) -> dict:
    try:
        tmx = pytmx.load_pygame(str(tmx_path), pixelalpha=True)
    except Exception:
        return {
            "tile_w": 0,
            "tile_h": 0,
            "map_w_px": 0,
            "map_h_px": 0,
            "portals": [],
        }
    portals: list[dict] = []
    for layer in tmx.layers:
        if not isinstance(layer, pytmx.TiledObjectGroup):
            continue
        if layer.name != "portals":
            continue
        for obj in layer:
            props = obj.properties or {}
            target = props.get("target_map")
            tx = props.get("target_position_x")
            ty = props.get("target_position_y")
            if not target or tx is None or ty is None:
                continue
            portals.append(
                {
                    "target_map": str(target),
                    "source_x": int(obj.x),
                    "source_y": int(obj.y),
                    "target_x": int(tx),
                    "target_y": int(ty),
                }
            )
    return {
        "tile_w": tmx.tilewidth,
        "tile_h": tmx.tileheight,
        "map_w_px": tmx.width * tmx.tilewidth,
        "map_h_px": tmx.height * tmx.tileheight,
        "portals": portals,
    }
