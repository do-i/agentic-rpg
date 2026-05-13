"""Build a node/edge graph of the scenario from portal connections.

Nodes are map ids (TMX file stems). Edges are directed portal links read
from the 'portals' object group in each TMX. Maps that fail to parse are
skipped, but still appear as nodes (the user should be able to see them
in the graph and click to investigate).
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


@dataclass(frozen=True)
class PortalRecord:
    source_tile: tuple[int, int]       # tile coordinates of the portal's top-left
    target_tile: tuple[int, int]       # destination tile on the target map


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


@dataclass
class GraphEdge:
    source: str
    target: str
    portals: tuple[PortalRecord, ...]

    @property
    def count(self) -> int:
        return len(self.portals)


@dataclass
class PortalGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    nodes_by_id: dict[str, GraphNode] = field(default_factory=dict)

    def edge_between(self, source: str, target: str) -> GraphEdge | None:
        for e in self.edges:
            if e.source == source and e.target == target:
                return e
        return None


def build_portal_graph(
    tmx_paths: list[Path],
    yaml_for: callable,
) -> PortalGraph:
    nodes: list[GraphNode] = []
    edge_buckets: dict[tuple[str, str], list[PortalRecord]] = {}

    for tmx_path in tmx_paths:
        map_id = tmx_path.stem
        yaml_path = yaml_for(tmx_path)
        meta = _read_yaml_meta(yaml_path) if yaml_path else _empty_meta()
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
            )
        )
        tw, th, records = _read_portal_records(tmx_path)
        for record in records:
            key = (map_id, record["target_map"])
            edge_buckets.setdefault(key, []).append(
                PortalRecord(
                    source_tile=(record["source_x"] // (tw or 1), record["source_y"] // (th or 1)),
                    target_tile=(record["target_x"], record["target_y"]),
                )
            )

    edges = [
        GraphEdge(source=s, target=t, portals=tuple(records))
        for (s, t), records in edge_buckets.items()
    ]
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


def _read_portal_records(tmx_path: Path) -> tuple[int, int, list[dict]]:
    try:
        tmx = pytmx.load_pygame(str(tmx_path), pixelalpha=True)
    except Exception:
        return 0, 0, []
    out: list[dict] = []
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
            out.append(
                {
                    "target_map": str(target),
                    "source_x": int(obj.x),
                    "source_y": int(obj.y),
                    "target_x": int(tx),
                    "target_y": int(ty),
                }
            )
    return tmx.tilewidth, tmx.tileheight, out
