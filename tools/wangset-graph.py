#!/usr/bin/env python3
"""Export Tiled TSX Wang terrain connections as graph files."""

# Usage:
#  python3 wangset-graph.py terrain-v7g.tsx --wangset "Terrains 01"
#

from __future__ import annotations

import argparse
import csv
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def safe_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not text or text[0].isdigit():
        text = f"n_{text}"
    return text


def dot_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def slug(value: str) -> str:
    text = value.lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "wangset"


def parse_wangid(value: str) -> list[int]:
    return [int(part) for part in value.split(",")]


def role_for_degree(degree: int, bridge: bool) -> str:
    if degree >= 4:
        return "hub"
    if degree <= 1:
        return "leaf"
    if bridge:
        return "bridge"
    return "branch"


def find_critical_points(nodes: set[str], adjacency: dict[str, set[str]]) -> tuple[set[tuple[str, str]], set[str]]:
    timer = 0
    visited: set[str] = set()
    tin: dict[str, int] = {}
    low: dict[str, int] = {}
    bridges: set[tuple[str, str]] = set()
    articulation_points: set[str] = set()

    def dfs(node: str, parent: str | None) -> None:
        nonlocal timer
        visited.add(node)
        tin[node] = timer
        low[node] = timer
        timer += 1
        child_count = 0

        for other in sorted(adjacency[node]):
            if other == parent:
                continue
            if other in visited:
                low[node] = min(low[node], tin[other])
                continue
            child_count += 1
            dfs(other, node)
            low[node] = min(low[node], low[other])
            if low[other] > tin[node]:
                bridges.add(tuple(sorted((node, other))))
            if parent is not None and low[other] >= tin[node]:
                articulation_points.add(node)

        if parent is None and child_count > 1:
            articulation_points.add(node)

    for node in sorted(nodes):
        if node not in visited:
            dfs(node, None)

    return bridges, articulation_points


def graph_for_wangset(wangset: ET.Element) -> dict[str, object]:
    colors = [color.attrib.get("name", f"Terrain_{index}") for index, color in enumerate(wangset.findall("wangcolor"), 1)]
    nodes = set(colors)
    edge_tiles: dict[tuple[str, str], set[int]] = defaultdict(set)

    for tile in wangset.findall("wangtile"):
        tile_id = int(tile.attrib["tileid"])
        ids = sorted(set(value for value in parse_wangid(tile.attrib.get("wangid", "")) if value))
        if len(ids) < 2:
            continue

        for offset, left_id in enumerate(ids):
            for right_id in ids[offset + 1 :]:
                left = colors[left_id - 1]
                right = colors[right_id - 1]
                edge_tiles[tuple(sorted((left, right)))].add(tile_id)

    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for left, right in edge_tiles:
        adjacency[left].add(right)
        adjacency[right].add(left)

    bridges, bridge_nodes = find_critical_points(nodes, adjacency)

    return {
        "name": wangset.attrib.get("name", "Wang Set"),
        "nodes": sorted(nodes),
        "edges": edge_tiles,
        "adjacency": adjacency,
        "bridges": bridges,
        "bridge_nodes": bridge_nodes,
    }


def write_dot(graphs: list[dict[str, object]], output_path: Path) -> None:
    lines = ["graph WangTerrainConnections {", "  graph [overlap=false, splines=true];", "  node [shape=ellipse, style=filled, fillcolor=\"#f8fafc\", color=\"#64748b\", fontname=\"Arial\"];", "  edge [color=\"#94a3b8\", fontname=\"Arial\"];"]

    for graph_index, graph in enumerate(graphs, 1):
        name = str(graph["name"])
        nodes = graph["nodes"]
        edges = graph["edges"]
        adjacency = graph["adjacency"]
        bridge_nodes = graph["bridge_nodes"]
        bridges = graph["bridges"]
        cluster_id = safe_id(f"cluster_{graph_index}_{name}")

        lines.append(f"  subgraph {cluster_id} {{")
        lines.append(f"    label=\"{dot_label(name)}\";")
        lines.append("    color=\"#cbd5e1\";")

        for node in nodes:
            degree = len(adjacency[node])
            role = role_for_degree(degree, node in bridge_nodes)
            fill = {
                "hub": "#fee2e2",
                "bridge": "#fef3c7",
                "branch": "#dbeafe",
                "leaf": "#dcfce7",
            }[role]
            lines.append(
                f"    {safe_id(name + '__' + node)} [label=\"{dot_label(node)}\\n{role} ({degree})\", fillcolor=\"{fill}\"];",
            )

        for (left, right), tiles in sorted(edges.items()):
            edge = tuple(sorted((left, right)))
            style = " penwidth=2.4 color=\"#f59e0b\"" if edge in bridges else ""
            lines.append(
                f"    {safe_id(name + '__' + left)} -- {safe_id(name + '__' + right)} [label=\"{len(tiles)}\"{style}];",
            )

        lines.append("  }")

    lines.append("}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(graphs: list[dict[str, object]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["wangset", "terrain", "role", "degree", "connections"])

        for graph in graphs:
            name = str(graph["name"])
            nodes = graph["nodes"]
            adjacency = graph["adjacency"]
            bridge_nodes = graph["bridge_nodes"]

            for node in nodes:
                connections = sorted(adjacency[node])
                writer.writerow([
                    name,
                    node,
                    role_for_degree(len(connections), node in bridge_nodes),
                    len(connections),
                    " ".join(connections),
                ])


def write_mermaid(graphs: list[dict[str, object]], output_path: Path) -> None:
    lines = ["```mermaid", "graph TD"]

    class_names = {
        "hub": "hub",
        "bridge": "bridge",
        "branch": "branch",
        "leaf": "leaf",
    }
    lines.extend([
        "  classDef hub fill:#fee2e2,stroke:#64748b,color:#111827;",
        "  classDef bridge fill:#fef3c7,stroke:#64748b,color:#111827;",
        "  classDef branch fill:#dbeafe,stroke:#64748b,color:#111827;",
        "  classDef leaf fill:#dcfce7,stroke:#64748b,color:#111827;",
        "  classDef bridgeEdge stroke:#f59e0b,stroke-width:3px;",
    ])
    edge_indexes_to_style: list[int] = []
    edge_index = 0

    for graph_index, graph in enumerate(graphs, 1):
        name = str(graph["name"])
        nodes = graph["nodes"]
        edges = graph["edges"]
        adjacency = graph["adjacency"]
        bridge_nodes = graph["bridge_nodes"]
        bridges = graph["bridges"]
        prefix = safe_id(f"g{graph_index}_{name}")

        lines.append(f"  subgraph {prefix}[\"{dot_label(name)}\"]")
        for node in nodes:
            degree = len(adjacency[node])
            role = role_for_degree(degree, node in bridge_nodes)
            node_id = safe_id(prefix + "__" + node)
            label = dot_label(f"{node}<br/>{role} ({degree})")
            lines.append(f"    {node_id}[\"{label}\"]")
            lines.append(f"    class {node_id} {class_names[role]}")

        for (left, right), tiles in sorted(edges.items()):
            left_id = safe_id(prefix + "__" + left)
            right_id = safe_id(prefix + "__" + right)
            lines.append(f"    {left_id} ---|{len(tiles)}| {right_id}")
            if tuple(sorted((left, right))) in bridges:
                edge_indexes_to_style.append(edge_index)
            edge_index += 1

        lines.append("  end")

    for index in edge_indexes_to_style:
        lines.append(f"  linkStyle {index} stroke:#f59e0b,stroke-width:3px;")

    lines.append("```")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_wangsets(root: ET.Element, requested_name: str | None) -> list[ET.Element]:
    wangsets = root.findall("./wangsets/wangset")
    if requested_name is None:
        return wangsets

    exact = [wangset for wangset in wangsets if wangset.attrib.get("name") == requested_name]
    if exact:
        return exact

    partial = [wangset for wangset in wangsets if requested_name in wangset.attrib.get("name", "")]
    if partial:
        return partial

    available = "\n".join(f"- {wangset.attrib.get('name', 'Wang Set')}" for wangset in wangsets)
    raise SystemExit(f"No Wang set matched {requested_name!r}. Available Wang sets:\n{available}")


def find_tilesets_dir() -> Path:
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir.parent / "rusted_kingdoms" / "assets" / "tilesets"
    if not candidate.is_dir():
        raise SystemExit(f"Tilesets directory not found: {candidate}")
    return candidate


def prompt_input_path() -> Path:
    tilesets_dir = find_tilesets_dir()
    tsx_files = sorted(tilesets_dir.rglob("*.tsx"))
    if not tsx_files:
        raise SystemExit(f"No .tsx files found in {tilesets_dir}")

    print(f"\nAvailable TSX files in {tilesets_dir}:")
    for index, path in enumerate(tsx_files, 1):
        print(f"  {index}) {path.relative_to(tilesets_dir)}")

    while True:
        raw = input(f"Select TSX file [1-{len(tsx_files)}]: ").strip()
        if not raw.isdigit():
            print("  Please enter a number.")
            continue
        choice = int(raw)
        if 1 <= choice <= len(tsx_files):
            return tsx_files[choice - 1]
        print(f"  Out of range: {choice}")


def prompt_wangset_choice(root: ET.Element) -> str | None:
    wangsets = root.findall("./wangsets/wangset")
    if not wangsets:
        raise SystemExit("No Wang sets found in the TSX file.")

    names = [wangset.attrib.get("name", f"Wang Set {index}") for index, wangset in enumerate(wangsets, 1)]
    print("\nAvailable Wang sets:")
    print("  0) <all>")
    for index, name in enumerate(names, 1):
        print(f"  {index}) {name}")

    while True:
        raw = input(f"Select Wang set [0-{len(names)}]: ").strip()
        if not raw.isdigit():
            print("  Please enter a number.")
            continue
        choice = int(raw)
        if choice == 0:
            return None
        if 1 <= choice <= len(names):
            return names[choice - 1]
        print(f"  Out of range: {choice}")


def prompt_output_formats() -> set[str]:
    options = ["dot", "csv", "mermaid"]
    print("\nAvailable output formats:")
    print("  0) <all>")
    for index, name in enumerate(options, 1):
        print(f"  {index}) {name}")

    while True:
        raw = input(f"Select formats (comma-separated, 0 for all) [0-{len(options)}]: ").strip()
        if not raw:
            print("  Please enter at least one number.")
            continue
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        if not all(part.isdigit() for part in parts):
            print("  Please enter numbers only.")
            continue
        choices = [int(part) for part in parts]
        if 0 in choices:
            return set(options)
        if any(choice < 1 or choice > len(options) for choice in choices):
            print(f"  Out of range. Valid: 0-{len(options)}")
            continue
        return {options[choice - 1] for choice in choices}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Wang terrain connection graphs from a TSX file.")
    parser.add_argument("input", type=Path, nargs="?", help="Input TSX file.")
    parser.add_argument("--wangset", help="Exact or partial Wang set name to export.")
    parser.add_argument("--dot", type=Path, help="Output Graphviz DOT file.")
    parser.add_argument("--csv", type=Path, help="Output CSV adjacency manifest.")
    parser.add_argument("--mermaid", type=Path, help="Output Mermaid graph file.")
    args = parser.parse_args()

    interactive = args.input is None
    input_path = args.input if args.input is not None else prompt_input_path()

    root = ET.parse(input_path).getroot()

    wangset_name = args.wangset
    if interactive and wangset_name is None:
        wangset_name = prompt_wangset_choice(root)

    explicit_formats = {name for name, value in (("dot", args.dot), ("csv", args.csv), ("mermaid", args.mermaid)) if value is not None}
    if interactive and not explicit_formats:
        formats = prompt_output_formats()
    elif explicit_formats:
        formats = explicit_formats
    else:
        formats = {"dot", "csv", "mermaid"}

    wangsets = choose_wangsets(root, wangset_name)
    graphs = [graph_for_wangset(wangset) for wangset in wangsets]

    default_base = input_path.with_suffix("")
    dot_path = args.dot or default_base.with_name(default_base.name + ".graph.dot")
    csv_path = args.csv or default_base.with_name(default_base.name + ".graph.csv")
    mermaid_path = args.mermaid or default_base.with_name(default_base.name + ".graph.mmd")

    if wangset_name and len(graphs) == 1:
        suffix = slug(str(graphs[0]["name"]))
        if args.dot is None:
            dot_path = default_base.with_name(default_base.name + f".{suffix}.graph.dot")
        if args.csv is None:
            csv_path = default_base.with_name(default_base.name + f".{suffix}.graph.csv")
        if args.mermaid is None:
            mermaid_path = default_base.with_name(default_base.name + f".{suffix}.graph.mmd")

    if "dot" in formats:
        write_dot(graphs, dot_path)
        print(f"Wrote {dot_path}")
    if "csv" in formats:
        write_csv(graphs, csv_path)
        print(f"Wrote {csv_path}")
    if "mermaid" in formats:
        write_mermaid(graphs, mermaid_path)
        print(f"Wrote {mermaid_path}")


if __name__ == "__main__":
    main()
