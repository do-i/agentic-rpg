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
class GraphNode:
    map_id: str
    tmx_path: Path
    yaml_path: Path | None
    display_name: str
    has_inn: bool
    has_shop: bool
    npc_count: int
    item_box_count: int


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    count: int  # number of portal objects from source pointing to target


@dataclass(frozen=True)
class PortalGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    nodes_by_id: dict[str, GraphNode] = field(default_factory=dict)


def build_portal_graph(
    tmx_paths: list[Path],
    yaml_for: callable,
) -> PortalGraph:
    nodes: list[GraphNode] = []
    edge_counts: dict[tuple[str, str], int] = {}

    for tmx_path in tmx_paths:
        map_id = tmx_path.stem
        yaml_path = yaml_for(tmx_path)
        meta = _read_yaml_meta(yaml_path) if yaml_path else {}
        nodes.append(
            GraphNode(
                map_id=map_id,
                tmx_path=tmx_path,
                yaml_path=yaml_path,
                display_name=meta.get("name") or map_id,
                has_inn=meta.get("has_inn", False),
                has_shop=meta.get("has_shop", False),
                npc_count=meta.get("npc_count", 0),
                item_box_count=meta.get("item_box_count", 0),
            )
        )
        for target in _read_portal_targets(tmx_path):
            key = (map_id, target)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = [GraphEdge(source=s, target=t, count=c) for (s, t), c in edge_counts.items()]
    nodes_by_id = {n.map_id: n for n in nodes}
    return PortalGraph(nodes=nodes, edges=edges, nodes_by_id=nodes_by_id)


def _read_yaml_meta(yaml_path: Path) -> dict:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "name": data.get("name"),
        "has_inn": "inn" in data,
        "has_shop": "shop" in data,
        "npc_count": len(data.get("npcs") or []),
        "item_box_count": len(data.get("item_boxes") or []),
    }


def _read_portal_targets(tmx_path: Path) -> list[str]:
    try:
        tmx = pytmx.load_pygame(str(tmx_path), pixelalpha=True)
    except Exception:
        return []
    targets: list[str] = []
    for layer in tmx.layers:
        if not isinstance(layer, pytmx.TiledObjectGroup):
            continue
        if layer.name != "portals":
            continue
        for obj in layer:
            target = (obj.properties or {}).get("target_map")
            if target:
                targets.append(str(target))
    return targets
