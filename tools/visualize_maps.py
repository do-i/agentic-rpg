#!/usr/bin/env python
"""
visualize_maps.py — Render an interactive HTML graph of map connections.

Usage:
    python tools/visualize_maps.py --root rusted_kingdoms --out maps_graph.html

Reads map YAML files for metadata, and TMX files for portal edges
(`objectgroup name="portals"` with `target_map` property). Emits a
self-contained HTML file that uses vis-network (loaded from CDN) to
render the graph. Click a node to see its details in the side panel.
"""

import argparse
import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


def render_screenshots(tmx_dir: Path, out_dir: Path, max_width: int = 1200) -> dict[str, str]:
    """Render each TMX file's visible tile layers to a PNG.

    Returns {map_id: relative_png_path} for HTML embedding.
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    import pytmx

    pygame.init()
    pygame.display.set_mode((1, 1))
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered: dict[str, str] = {}
    for tmx_path in sorted(tmx_dir.glob("*.tmx")):
        map_id = tmx_path.stem
        try:
            tmx = pytmx.load_pygame(str(tmx_path), pixelalpha=True)
        except Exception as e:
            print(f"  ! skip {map_id}: {e}")
            continue
        tw, th = tmx.tilewidth, tmx.tileheight
        w_px, h_px = tmx.width * tw, tmx.height * th
        surf = pygame.Surface((w_px, h_px), pygame.SRCALPHA)
        for layer in tmx.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, image in layer.tiles():
                surf.blit(image, (x * tw, y * th))
        # Down-scale large maps to keep HTML responsive.
        if w_px > max_width:
            scale = max_width / w_px
            new_size = (int(w_px * scale), int(h_px * scale))
            surf = pygame.transform.smoothscale(surf, new_size)
        png_path = out_dir / f"{map_id}.png"
        pygame.image.save(surf, str(png_path))
        rendered[map_id] = png_path.name  # relative to out_dir
    pygame.quit()
    return rendered


def load_yaml(path: Path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def map_id_from_path(path: Path) -> str:
    return path.stem


def collect_map_metadata(maps_dir: Path) -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for yaml_path in sorted(maps_dir.glob("*.yaml")):
        data = load_yaml(yaml_path)
        mid = data.get("id") or map_id_from_path(yaml_path)
        npcs = data.get("npcs") or []
        item_boxes = data.get("item_boxes") or []
        nodes[mid] = {
            "id": mid,
            "yaml_file": str(yaml_path.relative_to(maps_dir.parent.parent)),
            "name": data.get("name", mid),
            "bgm": data.get("bgm"),
            "has_inn": "inn" in data,
            "has_shop": "shop" in data,
            "has_apothecary": "apothecary" in data,
            "has_magic_core_shop": "magic_core_shop" in data,
            "transport": data.get("transport"),
            "encounter": data.get("encounter") or data.get("enemy_spawn"),
            "npc_count": len(npcs),
            "npcs": [
                {"id": n.get("id"), "type": n.get("type"),
                 "dialogue": n.get("dialogue"), "position": n.get("position"),
                 "sprite": n.get("sprite")}
                for n in npcs
                if isinstance(n, dict)
            ],
            "item_box_count": len(item_boxes),
            "item_boxes": [
                {"id": b.get("id"), "position": b.get("position")}
                for b in item_boxes
                if isinstance(b, dict)
            ],
        }
    return nodes


DEFAULT_ITEM_BOX_SPRITE = "assets/sprites/objects/item_box.tsx"


def resolve_sprite(scenario_root: Path, sprite_rel: str,
                   assets_dir: Path, cache: dict) -> dict | None:
    """Read a .tsx sheet, copy its PNG into <assets_dir>/sprites/, return spec.

    Returns {url, sheet_cols, sheet_rows, tile_w, tile_h} or None on failure.
    Url is relative to the HTML output (sibling of assets_dir).
    """
    if sprite_rel in cache:
        return cache[sprite_rel]
    src_tsx = scenario_root / sprite_rel
    if not src_tsx.exists():
        cache[sprite_rel] = None
        return None
    try:
        tree = ET.parse(src_tsx)
    except ET.ParseError:
        cache[sprite_rel] = None
        return None
    root = tree.getroot()
    tw = int(root.get("tilewidth") or 32)
    th = int(root.get("tileheight") or 32)
    img_el = root.find("image")
    if img_el is None or not img_el.get("source"):
        cache[sprite_rel] = None
        return None
    img_w = int(img_el.get("width") or tw)
    img_h = int(img_el.get("height") or th)
    cols = max(1, img_w // tw)
    rows = max(1, img_h // th)
    src_png = src_tsx.parent / img_el.get("source")
    if not src_png.exists():
        cache[sprite_rel] = None
        return None
    sub = src_tsx.parent.name
    dest_png = assets_dir / "sprites" / sub / src_png.name
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    if not dest_png.exists():
        shutil.copy2(src_png, dest_png)
    # Idle frame: NPC sheets follow engine layout (row 2 = DOWN, col 0 = idle).
    # Other sheets (objects, etc.) just use the first cell.
    idle_row = 2 if sub == "npc" and rows > 2 else 0
    idle_col = 0
    spec = {
        "url": f"{assets_dir.name}/sprites/{sub}/{src_png.name}",
        "sheet_cols": cols,
        "sheet_rows": rows,
        "tile_w": tw,
        "tile_h": th,
        "idle_col": idle_col,
        "idle_row": idle_row,
    }
    cache[sprite_rel] = spec
    return spec


def attach_sprites(nodes: dict, scenario_root: Path, assets_dir: Path) -> None:
    """Resolve and copy NPC/item-box sprites; attach a `sprite` spec to each entry."""
    cache: dict = {}
    for node in nodes.values():
        for n in node.get("npcs") or []:
            rel = n.get("sprite")
            if rel:
                n["sprite"] = resolve_sprite(scenario_root, rel, assets_dir, cache)
            else:
                n["sprite"] = None
        for b in node.get("item_boxes") or []:
            b["sprite"] = resolve_sprite(scenario_root, DEFAULT_ITEM_BOX_SPRITE, assets_dir, cache)


def collect_tmx_dims(tmx_dir: Path) -> dict[str, dict]:
    """Read map size + tile size from each TMX, keyed by map id."""
    dims: dict[str, dict] = {}
    for tmx_path in sorted(tmx_dir.glob("*.tmx")):
        try:
            tree = ET.parse(tmx_path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        dims[tmx_path.stem] = {
            "tile_w": int(root.get("tilewidth") or 16),
            "tile_h": int(root.get("tileheight") or 16),
            "map_w": int(root.get("width") or 0),
            "map_h": int(root.get("height") or 0),
        }
    return dims


def _int_property(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_tmx_portals(tmx_path: Path) -> dict | None:
    """Extract portal objects and editable TMX data from one map file."""
    try:
        xml_text = tmx_path.read_text()
        root = ET.fromstring(xml_text)
    except (OSError, ET.ParseError):
        return None

    tw = int(root.get("tilewidth") or 1)
    th = int(root.get("tileheight") or 1)
    map_w = int(root.get("width") or 0)
    map_h = int(root.get("height") or 0)
    portals: list[dict] = []

    for og in root.findall("objectgroup"):
        if (og.get("name") or "").lower() != "portals":
            continue
        for obj in og.findall("object"):
            name = obj.get("name") or ""
            ox = float(obj.get("x") or 0)
            oy = float(obj.get("y") or 0)
            ow = float(obj.get("width") or 0)
            oh = float(obj.get("height") or 0)
            src_tx = int(ox // tw)
            src_ty = int(oy // th)
            src_tw = max(1, int(ow // tw))
            src_th = max(1, int(oh // th))
            props = {
                prop.get("name"): prop.get("value")
                for prop in obj.findall("./properties/property")
                if prop.get("name")
            }
            tx = _int_property(props.get("target_position_x"))
            ty = _int_property(props.get("target_position_y"))
            portals.append({
                "id": obj.get("id"),
                "name": name,
                "bounds_px": [ox, oy, ow, oh],
                "source_pos": [src_tx, src_ty],
                "source_size": [src_tw, src_th],
                "target_map": props.get("target_map"),
                "target_pos": [tx, ty] if tx is not None and ty is not None else None,
            })

    return {
        "map_id": tmx_path.stem,
        "tmx_file": tmx_path.name,
        "xml": xml_text,
        "tile_w": tw,
        "tile_h": th,
        "map_w": map_w,
        "map_h": map_h,
        "portals": portals,
    }


def collect_portal_edit_data(tmx_dir: Path) -> dict[str, dict]:
    edit_data: dict[str, dict] = {}
    for tmx_path in sorted(tmx_dir.glob("*.tmx")):
        parsed = parse_tmx_portals(tmx_path)
        if parsed is not None:
            edit_data[parsed["map_id"]] = parsed
    return edit_data


def collect_portal_edges(tmx_dir: Path) -> list[dict]:
    edges: list[dict] = []
    for source, parsed in collect_portal_edit_data(tmx_dir).items():
        for portal in parsed["portals"]:
            target_map = portal.get("target_map")
            if target_map:
                edges.append({
                    "source": source,
                    "target": target_map,
                    "label": portal.get("name") or "",
                    "portal_id": portal.get("id"),
                    "source_pos": portal.get("source_pos"),
                    "source_size": portal.get("source_size"),
                    "target_pos": portal.get("target_pos"),
                })
    return edges


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Map Connections — __TITLE__</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  :root {
__ROOT_VARS__
  }
  html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, system-ui, sans-serif; background: var(--ui-background); color: var(--ui-text); }
  a { color: var(--ui-link); text-decoration: none; }
  a:hover { text-decoration: underline; }
  #app { display: flex; height: 100vh; }
  #graph { position: relative; flex: 1; min-width: 100px; background: var(--ui-graph_bg); }
  #network { position: absolute; inset: 0; }
  #splitter { width: 6px; cursor: col-resize; background: var(--ui-splitter); flex: 0 0 6px; transition: background 0.1s; }
  #splitter:hover, #splitter.dragging { background: var(--ui-splitter_hover); }
  #panel { width: 360px; min-width: 200px; padding: 16px 20px; overflow-y: auto; background: var(--ui-panel_bg); border-left: 1px solid var(--ui-border); box-sizing: border-box; }
  body.dragging, body.dragging * { cursor: col-resize !important; user-select: none; }
  h1 { font-size: 13px; margin: 0 0 12px; color: var(--ui-subheading); text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
  h2 { font-size: 18px; margin: 8px 0 4px; color: var(--ui-heading); font-weight: 600; }
  p { margin: 8px 0; }
  .muted { color: var(--ui-text_muted); font-size: 12px; }
  .badge { display: inline-block; padding: 2px 9px; margin: 2px 4px 2px 0; border-radius: 10px; background: var(--badge-default_bg); color: var(--badge-text); font-size: 11px; font-weight: 500; }
  .badge.inn { background: var(--badge-inn_bg); }
  .badge.shop { background: var(--badge-shop_bg); }
  .badge.apo { background: var(--badge-apothecary_bg); }
  .badge.transport { background: var(--badge-transport_bg); }
  ul { padding-left: 18px; margin: 6px 0; }
  li { margin: 3px 0; font-size: 13px; }
  details { margin: 8px 0; }
  summary { cursor: pointer; color: var(--ui-text_muted); font-size: 13px; padding: 2px 0; }
  summary:hover { color: var(--ui-text); }
  code { background: var(--ui-code_bg); color: var(--ui-code_text); padding: 1px 5px; border-radius: 3px; font-size: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .empty { color: var(--ui-empty); font-style: italic; }
  .legend { font-size: 11px; color: var(--ui-text_muted); margin: -4px 0 12px; display: flex; gap: 14px; flex-wrap: wrap; }
  .legend-item { display: inline-flex; align-items: center; gap: 6px; }
  .swatch { display: inline-block; width: 12px; height: 12px; box-sizing: border-box; }
  .swatch.out { border: 2px solid #ff4a2a; border-radius: 2px; background: rgba(255,74,42,0.25); }
  .swatch.in  { border: 2px solid #3acfff; border-radius: 50%; background: rgba(58,207,255,0.25); }
  .swatch.npc { border: 2px solid #4ad04a; border-radius: 50%; background: rgba(74,208,74,0.35); }
  .swatch.item { border: 2px solid #d0a04a; border-radius: 2px; background: rgba(208,160,74,0.4); }
  .toggles { display: flex; gap: 14px; flex-wrap: wrap; margin: 0 0 10px; }
  .toggle { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; font-size: 12px; color: var(--ui-text_muted); }
  .toggle input { accent-color: var(--ui-heading); }
  .mapping-toolbar { position: absolute; left: 14px; top: 14px; z-index: 20; display: flex; align-items: center; gap: 10px; max-width: calc(100% - 28px); padding: 10px 12px; border: 1px solid var(--ui-border); border-radius: 6px; background: rgba(10, 14, 20, 0.88); box-shadow: 0 8px 24px rgba(0,0,0,0.35); backdrop-filter: blur(4px); }
  .mapping-toggle { display: inline-flex; align-items: center; gap: 7px; white-space: nowrap; cursor: pointer; user-select: none; font-size: 13px; color: var(--ui-text); }
  .mapping-toggle input { accent-color: var(--ui-heading); }
  .mapping-status { color: var(--ui-heading); font-size: 13px; font-weight: 600; }
  .mapping-substatus { color: var(--ui-text_muted); font-size: 12px; max-width: 460px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mapping-dirty { color: var(--ui-text_muted); font-size: 12px; white-space: nowrap; }
  .editor-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 6px 0; }
  .editor-button { border: 1px solid var(--ui-border); border-radius: 4px; background: var(--ui-code_bg); color: var(--ui-text); padding: 5px 8px; font-size: 12px; cursor: pointer; }
  .editor-button:disabled { opacity: 0.45; cursor: not-allowed; }
  .editor-pill { display: inline-block; border: 1px solid var(--ui-border); border-radius: 999px; padding: 2px 8px; font-size: 11px; color: var(--ui-text_muted); }
  .editor-dirty-list { max-height: 90px; overflow: auto; margin: 6px 0 0; padding-left: 16px; }
  body.editor-mode .screenshot { cursor: crosshair; }
  body.editor-mode .map-marker.out { pointer-events: auto; cursor: pointer; }
  .map-marker.selected { outline: 3px solid #fff; outline-offset: 3px; }
  .pending-line { position: absolute; height: 3px; transform-origin: 0 50%; background: #fff; box-shadow: 0 0 8px #ff4a2a; pointer-events: none; z-index: 3; }
  #tile-modal { position: fixed; inset: 0; display: none; align-items: center; justify-content: center; background: var(--ui-lightbox_bg); z-index: 120; }
  #tile-modal.open { display: flex; }
  .tile-dialog { width: min(94vw, 1100px); max-height: 92vh; display: flex; flex-direction: column; border: 1px solid var(--ui-border); border-radius: 6px; background: var(--ui-panel_bg); box-shadow: 0 18px 60px rgba(0,0,0,0.55); overflow: hidden; }
  .tile-dialog-header { display: flex; align-items: center; gap: 12px; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--ui-border); }
  .tile-dialog-title { font-size: 15px; font-weight: 600; color: var(--ui-heading); }
  .tile-dialog-body { padding: 12px 14px 14px; overflow: auto; }
  .tile-error { min-height: 18px; color: #ff9c8b; font-size: 12px; margin-bottom: 8px; }
  .tile-picker-wrap { position: relative; display: inline-block; max-width: 100%; line-height: 0; background: #000; border: 1px solid var(--ui-screenshot_border); }
  #tile-modal-img { display: block; max-width: 100%; max-height: 74vh; image-rendering: pixelated; cursor: crosshair; }
  #tile-modal-overlays { position: absolute; inset: 0; pointer-events: none; }
  .tile-cell-marker { position: absolute; box-sizing: border-box; border: 2px solid #fff; background: rgba(255,255,255,0.18); box-shadow: 0 0 10px rgba(255,255,255,0.8); }
  .tile-cell-marker.source { border-color: #ffd200; box-shadow: 0 0 10px #ff4a2a; }
  .tile-cell-marker.dest { border-color: #3acfff; box-shadow: 0 0 10px #3acfff; }
  .sprite { position: absolute; pointer-events: none; box-sizing: border-box; }
  .sprite.npc  { border: 2px solid #4ad04a; background: rgba(74,208,74,0.35); border-radius: 50%; box-shadow: 0 0 0 1px rgba(0,0,0,0.6); }
  .sprite.item { border: 2px solid #d0a04a; background: rgba(208,160,74,0.45); border-radius: 2px; box-shadow: 0 0 0 1px rgba(0,0,0,0.6); }
  .sprite.has-image { border: none; background-color: transparent; box-shadow: none; border-radius: 0; }
  body.hide-sprites .sprite { display: none; }
  body.hide-outbound .map-marker.out { display: none; }
  body.hide-inbound  .map-marker.in  { display: none; }
  .screenshot { width: 100%; margin: 8px 0; border: 1px solid var(--ui-screenshot_border); border-radius: 4px; image-rendering: pixelated; cursor: zoom-in; background: #000; display: block; }
  .map-wrap { position: relative; margin: 8px 0; }
  .map-wrap .screenshot { margin: 0; }
  .map-marker { position: absolute; pointer-events: none; box-sizing: border-box; background: rgba(255,255,255,0.15); animation: marker-pulse 0.8s ease-in-out infinite; }
  .map-marker::before { content: ""; position: absolute; inset: -8px; pointer-events: none; }
  .map-marker::after { content: ""; position: absolute; left: 50%; top: 50%; width: 8px; height: 8px; margin: -4px 0 0 -4px; border-radius: 50%; animation: marker-blink 0.45s steps(2, end) infinite; }
  /* OUT — you leave from here: orange/red square, expanding ring outward */
  .map-marker.out { border: 3px solid #ff4a2a; border-radius: 2px; box-shadow: 0 0 0 2px rgba(0,0,0,0.6), 0 0 14px #ff4a2a, 0 0 28px rgba(255,74,42,0.6); }
  .map-marker.out::before { border: 2px solid #ffd200; border-radius: 3px; animation: marker-ring-out 1.2s ease-out infinite; }
  .map-marker.out::after { background: #ffd200; box-shadow: 0 0 8px #ffd200, 0 0 16px #ff4a2a; }
  /* IN — you arrive here: cyan diamond, contracting ring inward */
  .map-marker.in { border: 3px solid #3acfff; border-radius: 50%; box-shadow: 0 0 0 2px rgba(0,0,0,0.6), 0 0 14px #3acfff, 0 0 28px rgba(58,207,255,0.6); }
  .map-marker.in::before { border: 2px dashed #b8f3ff; border-radius: 50%; animation: marker-ring-in 1.2s ease-in infinite; }
  .map-marker.in::after { background: #b8f3ff; box-shadow: 0 0 8px #b8f3ff, 0 0 16px #3acfff; }
  @keyframes marker-pulse { 0%, 100% { transform: scale(1.0); } 50% { transform: scale(1.15); } }
  @keyframes marker-ring-out { 0% { transform: scale(0.9); opacity: 0.9; } 100% { transform: scale(1.8); opacity: 0; } }
  @keyframes marker-ring-in  { 0% { transform: scale(2.0); opacity: 0; } 60% { opacity: 0.9; } 100% { transform: scale(0.95); opacity: 0; } }
  @keyframes marker-blink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0.25; } }
  #lightbox { position: fixed; inset: 0; background: var(--ui-lightbox_bg); display: none; align-items: center; justify-content: center; z-index: 100; cursor: zoom-out; }
  #lightbox-frame { position: relative; display: inline-block; line-height: 0; }
  #lightbox-img { display: block; max-width: 95vw; max-height: 95vh; image-rendering: pixelated; }
  #lightbox-markers { position: absolute; inset: 0; pointer-events: none; }
  #lightbox-markers .map-marker { border-width: 4px; }
</style>
</head>
<body>
<div id="app">
  <div id="graph">
    <div id="network"></div>
    <div class="mapping-toolbar">
      <label class="mapping-toggle"><input type="checkbox" id="mapping-toggle"> Mapping Edit Mode</label>
      <span id="mapping-status" class="mapping-status">Off</span>
      <span id="mapping-substatus" class="mapping-substatus">Turn on to retarget portals from the graph.</span>
      <span id="mapping-dirty" class="mapping-dirty"></span>
    </div>
  </div>
  <div id="splitter" title="Drag to resize"></div>
  <div id="panel">
    <h1>Map Details</h1>
    <div class="legend">
      <span class="legend-item"><span class="swatch out"></span> outbound</span>
      <span class="legend-item"><span class="swatch in"></span> inbound</span>
      <span class="legend-item"><span class="swatch npc"></span> NPC</span>
      <span class="legend-item"><span class="swatch item"></span> item box</span>
    </div>
    <div class="toggles">
      <label class="toggle"><input type="checkbox" id="sprite-toggle"   checked> sprites</label>
      <label class="toggle"><input type="checkbox" id="outbound-toggle" checked> outbound</label>
      <label class="toggle"><input type="checkbox" id="inbound-toggle"  checked> inbound</label>
    </div>
    <div id="details" class="empty">Click a node to see details.</div>
  </div>
</div>
<div id="lightbox"><div id="lightbox-frame"><img id="lightbox-img" alt=""><div id="lightbox-markers"></div></div></div>
<div id="tile-modal">
  <div class="tile-dialog">
    <div class="tile-dialog-header">
      <div>
        <div id="tile-modal-title" class="tile-dialog-title">Select Tile</div>
        <div id="tile-modal-help" class="muted"></div>
      </div>
      <button id="tile-modal-cancel" class="editor-button">Cancel</button>
    </div>
    <div class="tile-dialog-body">
      <div id="tile-modal-error" class="tile-error"></div>
      <div class="tile-picker-wrap">
        <img id="tile-modal-img" alt="">
        <div id="tile-modal-overlays"></div>
      </div>
    </div>
  </div>
</div>
<script>
const NODES = __NODES__;
const EDGES = __EDGES__;
const COLORS = __COLORS__;
const TMX_EDIT_DATA = __TMX_EDIT_DATA__;

function classify(id, hasMeta) {
  const n = COLORS.node;
  if (!hasMeta) return n.missing;
  if (id.startsWith("zone_")) return n.zone;
  if (id.startsWith("port_")) return n.port;
  if (/_(inn|shop|house|apothecary)_/.test(id)) return n.building;
  if (id.startsWith("town_")) return n.town;
  return n.default;
}

const nodeIds = new Set(Object.keys(NODES));
EDGES.forEach(e => { if (!nodeIds.has(e.target)) nodeIds.add(e.target); });

const visNodes = [];
nodeIds.forEach(id => {
  const meta = NODES[id];
  const cls = classify(id, !!meta);
  const label = meta ? (meta.name || id) : id;
  visNodes.push({
    id,
    label: label + "\\n" + id,
    color: { background: cls.color, border: cls.border || COLORS.node.border, highlight: { background: cls.color, border: COLORS.node.border_selected } },
    shape: cls.shape,
    font: { color: COLORS.node.label_text, size: 13, multi: true },
    borderWidth: meta ? 1 : 2,
    borderWidthSelected: 3,
  });
});

const visEdges = EDGES.map((e, i) => ({
  id: "e" + i,
  from: e.source,
  to: e.target,
  label: e.label || "",
  arrows: "to",
  color: { color: COLORS.edge.line, highlight: COLORS.edge.highlight },
  font: { color: COLORS.edge.label_text, size: 11, strokeWidth: 0, align: "middle", background: COLORS.edge.label_bg },
  smooth: { type: "dynamic" },
}));

const edgeMap = {};
visEdges.forEach((ve, i) => { edgeMap[ve.id] = EDGES[i]; });

const container = document.getElementById("network");
const data = { nodes: new vis.DataSet(visNodes), edges: new vis.DataSet(visEdges) };
const options = {
  interaction: { hover: true, multiselect: false },
  physics: {
    solver: "forceAtlas2Based",
    forceAtlas2Based: { gravitationalConstant: -80, springLength: 140, springConstant: 0.05 },
    stabilization: { iterations: 200 },
  },
  nodes: { margin: 10 },
  edges: { selectionWidth: 2 },
};
const network = new vis.Network(container, data, options);

(function setupSplitter() {
  const splitter = document.getElementById("splitter");
  const panel = document.getElementById("panel");
  const app = document.getElementById("app");
  let dragging = false;
  splitter.addEventListener("mousedown", e => {
    dragging = true;
    splitter.classList.add("dragging");
    document.body.classList.add("dragging");
    e.preventDefault();
  });
  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    const rect = app.getBoundingClientRect();
    let w = rect.right - e.clientX;
    const min = 200, max = rect.width - 100 - 6;
    if (w < min) w = min;
    if (w > max) w = max;
    panel.style.width = w + "px";
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("dragging");
    document.body.classList.remove("dragging");
    network.redraw();
  });
})();

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const editorState = {
  enabled: false,
  step: "idle",
  sourceMap: null,
  sourcePortal: null,
  destMap: null,
  selected: null,
  currentMapId: null,
  edits: {},
  modal: null,
  lastMessage: "",
};

function portalKey(source, portalId) {
  return source + "::" + String(portalId);
}

function getPortal(source, portalId) {
  const data = TMX_EDIT_DATA[source];
  if (!data) return null;
  return (data.portals || []).find(p => String(p.id) === String(portalId)) || null;
}

function getPortalEdit(source, portalId) {
  return (editorState.edits[source] || {})[String(portalId)] || null;
}

function currentPortalTarget(source, portalId) {
  const portal = getPortal(source, portalId);
  if (!portal) return null;
  const edit = getPortalEdit(source, portalId);
  if (edit) return { target_map: edit.target_map, target_pos: [edit.target_position_x, edit.target_position_y] };
  return { target_map: portal.target_map, target_pos: portal.target_pos };
}

function edgeWithCurrentTarget(edge) {
  if (!edge) return edge;
  if (!edge.portal_id) return edge;
  const current = currentPortalTarget(edge.source, edge.portal_id);
  if (!current) return edge;
  return Object.assign({}, edge, {
    target: current.target_map || edge.target,
    target_pos: current.target_pos || edge.target_pos,
  });
}

function setPortalEdit(source, portalId, targetMap, tileX, tileY) {
  if (!editorState.edits[source]) editorState.edits[source] = {};
  editorState.edits[source][String(portalId)] = {
    target_map: targetMap,
    target_position_x: tileX,
    target_position_y: tileY,
  };
  refreshEditedEdges();
}

function refreshEditedEdges() {
  Object.entries(edgeMap).forEach(([edgeId, edge]) => {
    const current = edgeWithCurrentTarget(edge);
    if (current && data.edges.get(edgeId)) {
      data.edges.update({ id: edgeId, to: current.target, label: current.label || "" });
    }
  });
}

function dirtyEntries() {
  const entries = [];
  Object.entries(editorState.edits).forEach(([source, byPortal]) => {
    Object.entries(byPortal).forEach(([portalId, edit]) => {
      const original = getPortal(source, portalId);
      if (!original) return;
      const same = original.target_map === edit.target_map
        && original.target_pos
        && original.target_pos[0] === edit.target_position_x
        && original.target_pos[1] === edit.target_position_y;
      if (!same) entries.push({ source, portalId, edit, original });
    });
  });
  return entries;
}

function updateEditorPanel() {
  const status = document.getElementById("mapping-status");
  const substatus = document.getElementById("mapping-substatus");
  const dirtyEl = document.getElementById("mapping-dirty");
  const dirty = dirtyEntries();
  if (!editorState.enabled) {
    status.textContent = "Off";
    substatus.textContent = editorState.lastMessage || "Turn on to retarget portals from the graph.";
  } else {
    status.textContent = instructionForStep();
    substatus.textContent = editorState.lastMessage || detailForStep();
  }
  dirtyEl.textContent = dirty.length ? dirty.length + " pending change" + (dirty.length === 1 ? "" : "s") : "";
}

function rerenderCurrentDetails() {
  if (!editorState.currentMapId) return;
  renderDetails(editorState.currentMapId);
}

function instructionForStep() {
  if (editorState.step === "source-node") return "Select Source Map Node";
  if (editorState.step === "source-tile") return "Select Source Tile";
  if (editorState.step === "dest-node") return "Select Destination Node";
  if (editorState.step === "dest-tile") return "Select Destination Tile";
  return "Mapping Edit Mode";
}

function detailForStep() {
  if (editorState.step === "source-node") return "Click a graph node for the map that contains the outbound portal.";
  if (editorState.step === "source-tile") return "Click an existing portal tile on " + editorState.sourceMap + ".";
  if (editorState.step === "dest-node") return "Click the graph node for the destination map.";
  if (editorState.step === "dest-tile") return "Click the arrival tile on " + editorState.destMap + ".";
  return "";
}

function startMappingEditMode() {
  editorState.enabled = true;
  editorState.step = "source-node";
  editorState.sourceMap = null;
  editorState.sourcePortal = null;
  editorState.destMap = null;
  editorState.selected = null;
  editorState.lastMessage = "";
  document.body.classList.add("editor-mode");
  updateEditorPanel();
}

function finishMappingEditMode() {
  editorState.enabled = false;
  editorState.step = "idle";
  editorState.sourceMap = null;
  editorState.sourcePortal = null;
  editorState.destMap = null;
  editorState.selected = null;
  document.body.classList.remove("editor-mode");
  closeTileModal();
  const dirty = dirtyEntries();
  if (dirty.length) {
    exportChangedMapsZip();
    editorState.lastMessage = "Downloaded map_portal_changes.zip with " + dirty.length + " changed portal" + (dirty.length === 1 ? "." : "s.");
  } else {
    editorState.lastMessage = "No mapping changes to export.";
  }
  updateEditorPanel();
}

function resetMappingCycle(message) {
  editorState.step = "source-node";
  editorState.sourceMap = null;
  editorState.sourcePortal = null;
  editorState.destMap = null;
  editorState.selected = null;
  editorState.lastMessage = message || "";
  if (network.unselectAll) network.unselectAll();
  updateEditorPanel();
}

function selectSourceMap(mapId) {
  const tmx = TMX_EDIT_DATA[mapId];
  if (!tmx || !(tmx.portals || []).length) {
    editorState.lastMessage = "Source map has no portal objects: " + mapId;
    updateEditorPanel();
    return;
  }
  editorState.sourceMap = mapId;
  editorState.step = "source-tile";
  editorState.lastMessage = "";
  updateEditorPanel();
  openTileModal(mapId, "source");
}

function selectDestinationMap(mapId) {
  editorState.destMap = mapId;
  editorState.step = "dest-tile";
  editorState.lastMessage = "";
  updateEditorPanel();
  openTileModal(mapId, "dest");
}

function handleMappingNodeClick(mapId) {
  if (editorState.step === "source-node") {
    selectSourceMap(mapId);
  } else if (editorState.step === "dest-node") {
    selectDestinationMap(mapId);
  }
}

function mapMetaForTilePicker(mapId) {
  const meta = NODES[mapId];
  const tmx = TMX_EDIT_DATA[mapId];
  if (!meta || !meta.screenshot || !meta.map_w || !meta.map_h) return null;
  return { meta, tmx };
}

function openTileModal(mapId, mode) {
  const bundle = mapMetaForTilePicker(mapId);
  if (!bundle) {
    editorState.lastMessage = "No screenshot or map dimensions available for " + mapId + ".";
    if (mode === "source") resetMappingCycle(editorState.lastMessage);
    else editorState.step = "dest-node";
    updateEditorPanel();
    return;
  }
  const modal = document.getElementById("tile-modal");
  const img = document.getElementById("tile-modal-img");
  document.getElementById("tile-modal-title").textContent = mode === "source" ? "Select Source Tile" : "Select Destination Tile";
  document.getElementById("tile-modal-help").textContent = mode === "source"
    ? "Click an existing portal tile on " + mapId + "."
    : "Click the destination arrival tile on " + mapId + ".";
  document.getElementById("tile-modal-error").textContent = "";
  document.getElementById("tile-modal-overlays").innerHTML = "";
  img.src = bundle.meta.screenshot;
  img.setAttribute("data-map-id", mapId);
  editorState.modal = { mapId, mode };
  renderTileModalOverlays(mapId, mode);
  modal.classList.add("open");
}

function closeTileModal() {
  document.getElementById("tile-modal").classList.remove("open");
  editorState.modal = null;
}

function tileFromModalEvent(ev) {
  const img = document.getElementById("tile-modal-img");
  const mapId = img.getAttribute("data-map-id");
  const meta = NODES[mapId];
  const rect = img.getBoundingClientRect();
  const relX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
  const relY = Math.max(0, Math.min(rect.height, ev.clientY - rect.top));
  return {
    mapId,
    x: Math.max(0, Math.min(meta.map_w - 1, Math.floor(relX / rect.width * meta.map_w))),
    y: Math.max(0, Math.min(meta.map_h - 1, Math.floor(relY / rect.height * meta.map_h))),
  };
}

function portalContainsTile(portal, x, y) {
  if (!portal || !portal.source_pos || !portal.source_size) return false;
  const px = portal.source_pos[0], py = portal.source_pos[1];
  const pw = portal.source_size[0], ph = portal.source_size[1];
  return x >= px && x < px + pw && y >= py && y < py + ph;
}

function findPortalAtTile(mapId, x, y) {
  const data = TMX_EDIT_DATA[mapId];
  const matches = ((data && data.portals) || [])
    .filter(p => portalContainsTile(p, x, y))
    .sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
  return matches[0] || null;
}

function renderTileModalOverlays(mapId, mode) {
  const overlays = document.getElementById("tile-modal-overlays");
  const meta = NODES[mapId];
  overlays.innerHTML = "";
  if (!meta || !meta.map_w || !meta.map_h) return;
  function addMarker(pos, size, cls, title) {
    if (!pos) return;
    const tw = (size && size[0]) || 1;
    const th = (size && size[1]) || 1;
    const div = document.createElement("div");
    div.className = "tile-cell-marker " + cls;
    div.title = title || "";
    div.style.left = (pos[0] / meta.map_w * 100).toFixed(3) + "%";
    div.style.top = (pos[1] / meta.map_h * 100).toFixed(3) + "%";
    div.style.width = (tw / meta.map_w * 100).toFixed(3) + "%";
    div.style.height = (th / meta.map_h * 100).toFixed(3) + "%";
    overlays.appendChild(div);
  }
  if (mode === "source") {
    ((TMX_EDIT_DATA[mapId] && TMX_EDIT_DATA[mapId].portals) || []).forEach(p => {
      addMarker(p.source_pos, p.source_size, "source", p.name || "portal #" + p.id);
    });
  } else if (editorState.sourcePortal && editorState.destMap === mapId) {
    const current = currentPortalTarget(editorState.sourceMap, editorState.sourcePortal.id);
    if (current && current.target_map === mapId) addMarker(current.target_pos, [1, 1], "dest", "current target");
  }
}

function handleTileModalClick(ev) {
  if (!editorState.modal) return;
  const tile = tileFromModalEvent(ev);
  if (editorState.modal.mode === "source") {
    const portal = findPortalAtTile(tile.mapId, tile.x, tile.y);
    if (!portal) {
      document.getElementById("tile-modal-error").textContent = "No existing portal object at tile [" + tile.x + "," + tile.y + "].";
      return;
    }
    editorState.sourcePortal = portal;
    editorState.selected = { source: tile.mapId, portalId: portal.id };
    editorState.step = "dest-node";
    editorState.lastMessage = "Source portal selected: " + tile.mapId + " #" + portal.id + ".";
    closeTileModal();
    updateEditorPanel();
  } else {
    setPortalEdit(editorState.sourceMap, editorState.sourcePortal.id, tile.mapId, tile.x, tile.y);
    const portalName = editorState.sourcePortal.name || "portal #" + editorState.sourcePortal.id;
    refreshEditedEdges();
    rerenderCurrentDetails();
    closeTileModal();
    resetMappingCycle("Changed " + editorState.sourceMap + " " + portalName + " -> " + tile.mapId + " [" + tile.x + "," + tile.y + "].");
  }
}

function renderDetails(id) {
  const el = document.getElementById("details");
  editorState.currentMapId = id;
  const meta = NODES[id];
  if (!meta) {
    el.classList.remove("empty");
    el.innerHTML = "<h2>" + escapeHtml(id) + "</h2><p class=\\"muted\\">No YAML metadata found — referenced as portal target only.</p>";
    updateEditorPanel();
    return;
  }
  const currentEdges = EDGES.map(edgeWithCurrentTarget);
  const incoming = currentEdges.filter(e => e.target === id);
  const outgoing = currentEdges.filter(e => e.source === id);

  const badges = [];
  if (meta.has_inn) badges.push('<span class="badge inn">inn</span>');
  if (meta.has_shop) badges.push('<span class="badge shop">shop</span>');
  if (meta.has_apothecary) badges.push('<span class="badge apo">apothecary</span>');
  if (meta.has_magic_core_shop) badges.push('<span class="badge shop">magic-core shop</span>');
  if (meta.transport) badges.push('<span class="badge transport">transport</span>');

  let html = "";
  html += "<h2>" + escapeHtml(meta.name) + "</h2>";
  html += '<div class="muted"><code>' + escapeHtml(id) + "</code></div>";
  if (meta.yaml_file) html += '<div class="muted">' + escapeHtml(meta.yaml_file) + "</div>";
  if (meta.screenshot) {
    const markers = [];
    outgoing.forEach(e => { if (e.source_pos) markers.push({ kind: "out", portalId: e.portal_id, source: e.source, pos: e.source_pos, size: e.source_size, label: "out: " + (e.label || "") + " -> " + e.target }); });
    incoming.forEach(e => { if (e.target_pos) markers.push({ kind: "in",  pos: e.target_pos, size: [1, 1], label: "in: " + e.source + " -> " + (e.label || "") }); });
    html += renderMapWithMarkers(meta, id, markers);
  }
  if (meta.tmx_only) html += '<p class="muted">No YAML metadata; TMX only.</p>';
  if (badges.length) html += '<div style="margin-top:8px">' + badges.join("") + "</div>";
  if (meta.bgm) html += '<p>BGM: <code>' + escapeHtml(meta.bgm) + "</code></p>";

  html += '<p>NPCs: ' + meta.npc_count + " &middot; Item boxes: " + meta.item_box_count + "</p>";

  if (meta.npcs && meta.npcs.length) {
    html += '<details open><summary>NPCs (' + meta.npcs.length + ')</summary><ul>';
    meta.npcs.forEach(n => {
      const pos = n.position ? ' <span class="muted">[' + n.position[0] + "," + n.position[1] + "]</span>" : "";
      html += "<li>" + escapeHtml(n.id || "?") + (n.type ? ' <span class="muted">(' + escapeHtml(n.type) + ")</span>" : "")
            + pos + (n.dialogue ? ' &rarr; <code>' + escapeHtml(n.dialogue) + "</code>" : "") + "</li>";
    });
    html += "</ul></details>";
  }

  if (meta.item_boxes && meta.item_boxes.length) {
    html += '<details><summary>Item boxes (' + meta.item_boxes.length + ')</summary><ul>';
    meta.item_boxes.forEach(b => {
      const pos = b.position ? ' <span class="muted">[' + b.position[0] + "," + b.position[1] + "]</span>" : "";
      html += "<li><code>" + escapeHtml(b.id || "?") + "</code>" + pos + "</li>";
    });
    html += "</ul></details>";
  }

  html += '<details open><summary>Outgoing portals (' + outgoing.length + ')</summary><ul>';
  outgoing.forEach(e => {
    const src = e.source_pos ? " from [" + e.source_pos[0] + "," + e.source_pos[1] + "]" : "";
    const pos = e.target_pos ? " @ [" + e.target_pos[0] + "," + e.target_pos[1] + "]" : "";
    html += '<li><a href="#" data-target="' + escapeHtml(e.target) + '">' + escapeHtml(e.label || "(unnamed)") + "</a>" + src + " &rarr; <code>" + escapeHtml(e.target) + "</code>" + pos + "</li>";
  });
  if (!outgoing.length) html += '<li class="muted">none</li>';
  html += "</ul></details>";

  html += '<details open><summary>Incoming portals (' + incoming.length + ')</summary><ul>';
  incoming.forEach(e => {
    const src = e.source_pos ? " [" + e.source_pos[0] + "," + e.source_pos[1] + "]" : "";
    const pos = e.target_pos ? " @ [" + e.target_pos[0] + "," + e.target_pos[1] + "]" : "";
    html += '<li><a href="#" data-target="' + escapeHtml(e.source) + '"><code>' + escapeHtml(e.source) + "</code></a>" + src + " &rarr; " + escapeHtml(e.label || "(unnamed)") + pos + "</li>";
  });
  if (!incoming.length) html += '<li class="muted">none</li>';
  html += "</ul></details>";

  el.classList.remove("empty");
  el.innerHTML = html;

  el.querySelectorAll("img[data-zoom]").forEach(img => {
    img.addEventListener("click", () => {
      if (editorState.enabled) return;
      const lb = document.getElementById("lightbox");
      const lbMarkers = document.getElementById("lightbox-markers");
      document.getElementById("lightbox-img").src = img.src;
      lbMarkers.innerHTML = "";
      const wrap = img.parentElement;
      if (wrap) {
        wrap.querySelectorAll(".map-marker, .sprite").forEach(m => {
          lbMarkers.appendChild(m.cloneNode(true));
        });
      }
      lb.style.display = "flex";
    });
  });

  attachEditorHandlers(el, id);
  updateEditorPanel();

  el.querySelectorAll("a[data-target]").forEach(a => {
    a.addEventListener("click", ev => {
      ev.preventDefault();
      const t = a.getAttribute("data-target");
      network.selectNodes([t]);
      network.focus(t, { scale: 1.0, animation: true });
      renderDetails(t);
    });
  });
}

function renderMapWithMarkers(meta, mapId, markers) {
  if (!meta || !meta.screenshot) return "";
  let html = '<div class="map-wrap">';
  html += '<img class="screenshot" data-zoom data-map-id="' + escapeHtml(mapId) + '" src="' + escapeHtml(meta.screenshot) + '" alt="' + escapeHtml(mapId) + '">';
  const mw = meta.map_w || 0, mh = meta.map_h || 0;
  if (mw > 0 && mh > 0) {
    const mapTW = meta.tile_w || 32, mapTH = meta.tile_h || 32;
    function spriteStyle(pos, sprite, fallbackTiles) {
      // returns inline-style string positioning a 1+ tile sprite at pos.
      const tilesW = sprite ? (sprite.tile_w / mapTW) : fallbackTiles;
      const tilesH = sprite ? (sprite.tile_h / mapTH) : fallbackTiles;
      const left = (pos[0] / mw * 100).toFixed(3);
      const top  = (pos[1] / mh * 100).toFixed(3);
      const w    = (tilesW / mw * 100).toFixed(3);
      const h    = (tilesH / mh * 100).toFixed(3);
      let s = "left:" + left + "%;top:" + top + "%;width:" + w + "%;height:" + h + "%;";
      if (sprite) {
        s += "background-image:url('" + sprite.url + "');";
        s += "background-size:" + (sprite.sheet_cols * 100) + "% " + (sprite.sheet_rows * 100) + "%;";
        const bgX = sprite.sheet_cols > 1 ? (sprite.idle_col / (sprite.sheet_cols - 1) * 100) : 0;
        const bgY = sprite.sheet_rows > 1 ? (sprite.idle_row / (sprite.sheet_rows - 1) * 100) : 0;
        s += "background-position:" + bgX.toFixed(3) + "% " + bgY.toFixed(3) + "%;";
        s += "background-repeat:no-repeat;image-rendering:pixelated;";
      }
      return s;
    }
    (meta.npcs || []).forEach(n => {
      if (!n.position) return;
      const lbl = "NPC: " + (n.id || "?") + (n.type ? " (" + n.type + ")" : "");
      const cls = n.sprite ? "sprite npc has-image" : "sprite npc";
      html += '<div class="' + cls + '" style="' + spriteStyle(n.position, n.sprite, 1) + '" title="' + escapeHtml(lbl) + '"></div>';
    });
    (meta.item_boxes || []).forEach(b => {
      if (!b.position) return;
      const cls = b.sprite ? "sprite item has-image" : "sprite item";
      html += '<div class="' + cls + '" style="' + spriteStyle(b.position, b.sprite, 1) + '" title="' + escapeHtml("item box: " + (b.id || "?")) + '"></div>';
    });
  }
  if (mw > 0 && mh > 0 && markers) {
    markers.forEach(m => {
      if (!m || !m.pos) return;
      const tw = (m.size && m.size[0]) || 1;
      const th = (m.size && m.size[1]) || 1;
      const left = (m.pos[0] / mw * 100).toFixed(3);
      const top  = (m.pos[1] / mh * 100).toFixed(3);
      const w    = (tw / mw * 100).toFixed(3);
      const h    = (th / mh * 100).toFixed(3);
      const title = m.label ? ' title="' + escapeHtml(m.label) + '"' : "";
      const kind = m.kind === "in" ? "in" : "out";
      const selected = editorState.selected
        && m.source === editorState.selected.source
        && String(m.portalId) === String(editorState.selected.portalId);
      let attrs = title;
      if (m.portalId != null && m.source) {
        attrs += ' data-source="' + escapeHtml(m.source) + '" data-portal-id="' + escapeHtml(m.portalId) + '"';
      }
      html += '<div class="map-marker ' + kind + (selected ? " selected" : "") + '" style="left:' + left + '%; top:' + top + '%; width:' + w + '%; height:' + h + '%"' + attrs + '></div>';
    });
  }
  const selected = editorState.selected;
  if (mw > 0 && mh > 0 && selected) {
    const current = currentPortalTarget(selected.source, selected.portalId);
    const portal = getPortal(selected.source, selected.portalId);
    if (portal && current && selected.source === mapId && current.target_map === mapId && current.target_pos) {
      const x1 = ((portal.source_pos[0] + portal.source_size[0] / 2) / mw * 100);
      const y1 = ((portal.source_pos[1] + portal.source_size[1] / 2) / mh * 100);
      const x2 = ((current.target_pos[0] + 0.5) / mw * 100);
      const y2 = ((current.target_pos[1] + 0.5) / mh * 100);
      const dx = x2 - x1, dy = y2 - y1;
      const length = Math.sqrt(dx * dx + dy * dy);
      const angle = Math.atan2(dy, dx) * 180 / Math.PI;
      html += '<div class="pending-line" style="left:' + x1.toFixed(3) + '%; top:' + y1.toFixed(3)
        + '%; width:' + length.toFixed(3) + '%; transform:rotate(' + angle.toFixed(3) + 'deg);"></div>';
    }
  }
  html += '</div>';
  return html;
}

function attachEditorHandlers(root, mapId) {
  // Mapping edit mode uses graph node clicks plus the modal tile picker.
  // Side-panel screenshots remain read-only so edit clicks are not swallowed by zoom/details behavior.
  return;
  root.querySelectorAll(".map-marker.out[data-portal-id]").forEach(marker => {
    marker.addEventListener("click", ev => {
      if (!editorState.enabled) return;
      ev.preventDefault();
      ev.stopPropagation();
      editorState.selected = {
        source: marker.getAttribute("data-source"),
        portalId: marker.getAttribute("data-portal-id"),
      };
      rerenderCurrentDetails();
    });
  });

  root.querySelectorAll("img.screenshot[data-map-id]").forEach(img => {
    img.addEventListener("click", ev => {
      if (!editorState.enabled || !editorState.selected) return;
      ev.preventDefault();
      ev.stopPropagation();
      const targetMap = img.getAttribute("data-map-id");
      const meta = NODES[targetMap];
      if (!meta || !meta.map_w || !meta.map_h) return;
      const rect = img.getBoundingClientRect();
      const relX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
      const relY = Math.max(0, Math.min(rect.height, ev.clientY - rect.top));
      const tileX = Math.max(0, Math.min(meta.map_w - 1, Math.floor(relX / rect.width * meta.map_w)));
      const tileY = Math.max(0, Math.min(meta.map_h - 1, Math.floor(relY / rect.height * meta.map_h)));
      setPortalEdit(editorState.selected.source, editorState.selected.portalId, targetMap, tileX, tileY);
      rerenderCurrentDetails();
    });
  });
}

function setProperty(doc, objectEl, name, value) {
  let propsEl = null;
  Array.from(objectEl.children).forEach(child => {
    if (child.tagName === "properties") propsEl = child;
  });
  if (!propsEl) {
    propsEl = doc.createElement("properties");
    objectEl.appendChild(propsEl);
  }
  let propEl = null;
  Array.from(propsEl.children).forEach(child => {
    if (child.tagName === "property" && child.getAttribute("name") === name) propEl = child;
  });
  if (!propEl) {
    propEl = doc.createElement("property");
    propEl.setAttribute("name", name);
    propsEl.appendChild(propEl);
  }
  propEl.setAttribute("value", String(value));
}

function serializeChangedMap(source) {
  const data = TMX_EDIT_DATA[source];
  const edits = editorState.edits[source];
  if (!data || !edits) return null;
  const doc = new DOMParser().parseFromString(data.xml, "application/xml");
  if (doc.querySelector("parsererror")) throw new Error("Could not parse embedded TMX for " + source);
  Object.entries(edits).forEach(([portalId, edit]) => {
    const objectEl = Array.from(doc.getElementsByTagName("object"))
      .find(el => el.getAttribute("id") === String(portalId));
    if (!objectEl) throw new Error("Portal object #" + portalId + " not found in " + source);
    setProperty(doc, objectEl, "target_map", edit.target_map);
    setProperty(doc, objectEl, "target_position_x", edit.target_position_x);
    setProperty(doc, objectEl, "target_position_y", edit.target_position_y);
  });
  return new XMLSerializer().serializeToString(doc);
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "application/xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportChangedMaps() {
  const sources = Array.from(new Set(dirtyEntries().map(d => d.source)));
  sources.forEach(source => {
    const xml = serializeChangedMap(source);
    if (xml != null) downloadText((TMX_EDIT_DATA[source].tmx_file || source + ".tmx"), xml);
  });
}

const CRC_TABLE = (() => {
  const table = [];
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dosDateTime(date) {
  const year = Math.max(1980, date.getFullYear());
  const dosTime = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const dosDate = ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { dosTime, dosDate };
}

function pushU16(out, value) {
  out.push(value & 0xff, (value >>> 8) & 0xff);
}

function pushU32(out, value) {
  out.push(value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff);
}

function makeZip(files) {
  const encoder = new TextEncoder();
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  const stamp = dosDateTime(new Date());

  files.forEach(file => {
    const nameBytes = encoder.encode(file.name);
    const dataBytes = encoder.encode(file.text);
    const crc = crc32(dataBytes);
    const local = [];
    pushU32(local, 0x04034b50);
    pushU16(local, 20);
    pushU16(local, 0x0800);
    pushU16(local, 0);
    pushU16(local, stamp.dosTime);
    pushU16(local, stamp.dosDate);
    pushU32(local, crc);
    pushU32(local, dataBytes.length);
    pushU32(local, dataBytes.length);
    pushU16(local, nameBytes.length);
    pushU16(local, 0);
    localParts.push(new Uint8Array(local), nameBytes, dataBytes);

    const central = [];
    pushU32(central, 0x02014b50);
    pushU16(central, 20);
    pushU16(central, 20);
    pushU16(central, 0x0800);
    pushU16(central, 0);
    pushU16(central, stamp.dosTime);
    pushU16(central, stamp.dosDate);
    pushU32(central, crc);
    pushU32(central, dataBytes.length);
    pushU32(central, dataBytes.length);
    pushU16(central, nameBytes.length);
    pushU16(central, 0);
    pushU16(central, 0);
    pushU16(central, 0);
    pushU16(central, 0);
    pushU32(central, 0);
    pushU32(central, offset);
    centralParts.push(new Uint8Array(central), nameBytes);
    offset += local.length + nameBytes.length + dataBytes.length;
  });

  const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0);
  const centralOffset = offset;
  const end = [];
  pushU32(end, 0x06054b50);
  pushU16(end, 0);
  pushU16(end, 0);
  pushU16(end, files.length);
  pushU16(end, files.length);
  pushU32(end, centralSize);
  pushU32(end, centralOffset);
  pushU16(end, 0);
  return new Blob([...localParts, ...centralParts, new Uint8Array(end)], { type: "application/zip" });
}

function exportChangedMapsZip() {
  const sources = Array.from(new Set(dirtyEntries().map(d => d.source)));
  if (!sources.length) return null;
  const files = sources.map(source => ({
    name: TMX_EDIT_DATA[source].tmx_file || source + ".tmx",
    text: serializeChangedMap(source),
  })).filter(file => file.text != null);
  if (!files.length) return null;
  const blob = makeZip(files);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "map_portal_changes.zip";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return blob;
}

function renderEdgeDetails(edgeId) {
  const el = document.getElementById("details");
  const e = edgeWithCurrentTarget(edgeMap[edgeId]);
  if (!e) return;
  editorState.currentMapId = e.source;
  const srcMeta = NODES[e.source];
  const tgtMeta = NODES[e.target];
  const srcName = srcMeta ? srcMeta.name : e.source;
  const tgtName = tgtMeta ? tgtMeta.name : e.target;
  const srcPos = e.source_pos ? "[" + e.source_pos[0] + "," + e.source_pos[1] + "]" : "(unknown)";
  const srcSize = e.source_size ? e.source_size[0] + "x" + e.source_size[1] : "?";
  const tgtPos = e.target_pos ? "[" + e.target_pos[0] + "," + e.target_pos[1] + "]" : "(unspecified)";

  let html = "";
  html += "<h2>Portal: " + escapeHtml(e.label || "(unnamed)") + "</h2>";
  html += '<div class="muted">edge</div>';
  html += "<p><strong>From:</strong> <a href=\\"#\\" data-target=\\"" + escapeHtml(e.source) + "\\">"
       + escapeHtml(srcName) + "</a> <code>" + escapeHtml(e.source) + "</code></p>";
  html += "<ul><li>tile: <code>" + srcPos + "</code> (size " + srcSize + ")</li></ul>";
  html += renderMapWithMarkers(srcMeta, e.source, [{ kind: "out", source: e.source, portalId: e.portal_id, pos: e.source_pos, size: e.source_size, label: e.label }]);
  html += "<p><strong>To:</strong> <a href=\\"#\\" data-target=\\"" + escapeHtml(e.target) + "\\">"
       + escapeHtml(tgtName) + "</a> <code>" + escapeHtml(e.target) + "</code></p>";
  html += "<ul><li>tile: <code>" + tgtPos + "</code></li></ul>";
  html += renderMapWithMarkers(tgtMeta, e.target, [{ kind: "in", pos: e.target_pos, size: [1, 1], label: e.label }]);

  el.classList.remove("empty");
  el.innerHTML = html;

  el.querySelectorAll("img[data-zoom]").forEach(img => {
    img.addEventListener("click", () => {
      if (editorState.enabled) return;
      const lb = document.getElementById("lightbox");
      const lbMarkers = document.getElementById("lightbox-markers");
      document.getElementById("lightbox-img").src = img.src;
      lbMarkers.innerHTML = "";
      const wrap = img.parentElement;
      if (wrap) {
        wrap.querySelectorAll(".map-marker, .sprite").forEach(m => {
          lbMarkers.appendChild(m.cloneNode(true));
        });
      }
      lb.style.display = "flex";
    });
  });

  attachEditorHandlers(el, e.source);

  el.querySelectorAll("a[data-target]").forEach(a => {
    a.addEventListener("click", ev => {
      ev.preventDefault();
      const t = a.getAttribute("data-target");
      network.selectNodes([t]);
      network.focus(t, { scale: 1.0, animation: true });
      renderDetails(t);
    });
  });
  updateEditorPanel();
}

[
  ["sprite-toggle",   "hide-sprites"],
  ["outbound-toggle", "hide-outbound"],
  ["inbound-toggle",  "hide-inbound"],
].forEach(([id, cls]) => {
  document.getElementById(id).addEventListener("change", e => {
    document.body.classList.toggle(cls, !e.target.checked);
  });
});

document.getElementById("mapping-toggle").addEventListener("change", e => {
  if (e.target.checked) startMappingEditMode();
  else finishMappingEditMode();
});

document.getElementById("tile-modal-img").addEventListener("click", handleTileModalClick);
document.getElementById("tile-modal-cancel").addEventListener("click", () => {
  closeTileModal();
  if (editorState.enabled) {
    if (editorState.step === "source-tile") resetMappingCycle("Source tile selection cancelled.");
    else if (editorState.step === "dest-tile") {
      editorState.step = "dest-node";
      editorState.destMap = null;
      editorState.lastMessage = "Destination tile selection cancelled.";
      updateEditorPanel();
    }
  }
});

network.on("click", params => {
  if (editorState.enabled) {
    if (params.nodes.length) handleMappingNodeClick(params.nodes[0]);
    return;
  }
  if (params.nodes.length) {
    renderDetails(params.nodes[0]);
  } else if (params.edges.length) {
    renderEdgeDetails(params.edges[0]);
  }
});

document.getElementById("lightbox").addEventListener("click", () => {
  document.getElementById("lightbox").style.display = "none";
});

window.__portalEditorTest = {
  editorState,
  setPortalEdit,
  dirtyEntries,
  serializeChangedMap,
  makeZip,
  exportChangedMapsZip,
  handleMappingNodeClick,
  findPortalAtTile,
  handleTileModalClick,
  currentPortalTarget,
};
updateEditorPanel();
</script>
</body>
</html>
"""


def load_colors(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(
            f"colors file not found: {path}\n"
            f"  Expected a YAML palette at this location.\n"
            f"  Example: see tools/visualize_maps_colors.yaml"
        )
    return load_yaml(path)


def build_root_vars(colors: dict) -> str:
    """Flatten {section: {key: value}} into CSS custom properties.

    Skips nested dicts (used by JS for node styles).
    """
    lines = []
    for section, entries in colors.items():
        if not isinstance(entries, dict):
            continue
        for key, value in entries.items():
            if isinstance(value, (dict, list)):
                continue
            lines.append(f"    --{section}-{key}: {value};")
    return "\n".join(lines)


def build_html(title: str, nodes: dict, edges: list, colors: dict, tmx_edit_data: dict | None = None) -> str:
    return (
        HTML_TEMPLATE
        .replace("__TITLE__", title)
        .replace("__ROOT_VARS__", build_root_vars(colors))
        .replace("__NODES__", json.dumps(nodes, indent=2))
        .replace("__EDGES__", json.dumps(edges, indent=2))
        .replace("__COLORS__", json.dumps(colors, indent=2))
        .replace("__TMX_EDIT_DATA__", json.dumps(tmx_edit_data or {}, indent=2))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("rusted_kingdoms"),
                        help="Scenario root containing manifest.yaml")
    parser.add_argument("--out", type=Path, default=Path("maps_graph.html"),
                        help="Output HTML file")
    parser.add_argument("--no-screenshots", action="store_true",
                        help="Skip rendering map screenshots (faster, no pygame needed)")
    parser.add_argument("--screenshot-width", type=int, default=1200,
                        help="Max screenshot width in px (downscaled if larger)")
    parser.add_argument("--colors", type=Path,
                        default=Path(__file__).parent / "visualize_maps_colors.yaml",
                        help="YAML palette file controlling all UI/graph colors")
    args = parser.parse_args()

    colors = load_colors(args.colors)

    manifest_path = args.root / "manifest.yaml"
    if not manifest_path.exists():
        raise SystemExit(f"manifest.yaml not found at {manifest_path}")
    manifest = load_yaml(manifest_path)

    maps_dir = args.root / (manifest.get("refs", {}).get("maps") or "data/maps")
    tmx_dir = args.root / (manifest.get("refs", {}).get("tmx") or "assets/maps")

    nodes = collect_map_metadata(maps_dir)
    tmx_edit_data = collect_portal_edit_data(tmx_dir)
    edges = collect_portal_edges(tmx_dir)
    dims = collect_tmx_dims(tmx_dir)
    for mid, d in dims.items():
        if mid in nodes:
            nodes[mid].update(d)

    assets_dir = args.out.with_suffix("").parent / f"{args.out.stem}.assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    attach_sprites(nodes, args.root, assets_dir)

    if not args.no_screenshots:
        print(f"Rendering screenshots into {assets_dir}/ ...")
        rendered = render_screenshots(tmx_dir, assets_dir, max_width=args.screenshot_width)
        rel_dir = assets_dir.name
        for mid, png_name in rendered.items():
            rel_path = f"{rel_dir}/{png_name}"
            if mid in nodes:
                nodes[mid]["screenshot"] = rel_path
            else:
                nodes[mid] = {
                    "id": mid, "name": mid, "yaml_file": "",
                    "bgm": None, "has_inn": False, "has_shop": False,
                    "has_apothecary": False, "has_magic_core_shop": False,
                    "transport": None, "encounter": None,
                    "npc_count": 0, "npcs": [], "item_box_count": 0, "item_boxes": [],
                    "screenshot": rel_path, "tmx_only": True,
                }
                if mid in dims:
                    nodes[mid].update(dims[mid])

    title = manifest.get("name", str(args.root))
    html = build_html(title, nodes, edges, colors, tmx_edit_data)
    args.out.write_text(html)

    referenced = {e["target"] for e in edges} | {e["source"] for e in edges}
    missing = sorted(referenced - set(nodes))
    print(f"Wrote {args.out}: {len(nodes)} nodes, {len(edges)} edges")
    if missing:
        print(f"  ({len(missing)} portal targets without YAML metadata: {', '.join(missing)})")


if __name__ == "__main__":
    main()
