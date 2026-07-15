// Dagre-based initial layout for the portal graph.
//
// Node display size mirrors the pygame editor's thumbnail bounds: each map is
// scaled into a THUMB_MAX_W x THUMB_MAX_H box (never upscaled) plus a label
// strip, so layout spacing tracks real thumbnail footprints.

import dagre from "dagre";
import type { MapNodeInfo, PortalEdgeInfo } from "./api";

export const THUMB_MAX_W = 256;
export const THUMB_MAX_H = 192;
export const LABEL_STRIP_H = 22;

export interface NodeBox {
  width: number;
  height: number;
  thumbWidth: number;
  thumbHeight: number;
}

export function nodeBox(info: MapNodeInfo): NodeBox {
  const [mapW, mapH] = info.map_size_px;
  const safeW = Math.max(1, mapW);
  const safeH = Math.max(1, mapH);
  const scale = Math.min(THUMB_MAX_W / safeW, THUMB_MAX_H / safeH, 1.0);
  const thumbWidth = Math.max(48, Math.round(safeW * scale));
  const thumbHeight = Math.max(36, Math.round(safeH * scale));
  return {
    width: thumbWidth,
    height: thumbHeight + LABEL_STRIP_H,
    thumbWidth,
    thumbHeight,
  };
}

export function layoutGraph(
  nodes: MapNodeInfo[],
  edges: PortalEdgeInfo[],
): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 140, marginx: 40, marginy: 40 });
  g.setDefaultEdgeLabel(() => ({}));

  for (const node of nodes) {
    const box = nodeBox(node);
    g.setNode(node.map_id, { width: box.width, height: box.height });
  }
  // Deduplicate undirected pairs so reciprocal portals don't double-pull.
  const seen = new Set<string>();
  for (const edge of edges) {
    if (edge.source === edge.target) continue;
    if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) continue;
    const key =
      edge.source < edge.target
        ? `${edge.source}|${edge.target}`
        : `${edge.target}|${edge.source}`;
    if (seen.has(key)) continue;
    seen.add(key);
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const positions = new Map<string, { x: number; y: number }>();
  for (const node of nodes) {
    const placed = g.node(node.map_id);
    const box = nodeBox(node);
    // dagre returns centers; React Flow wants top-left corners.
    positions.set(node.map_id, {
      x: placed.x - box.width / 2,
      y: placed.y - box.height / 2,
    });
  }
  return positions;
}
