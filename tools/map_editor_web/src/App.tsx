import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import type { Edge, EdgeMouseHandler, NodeMouseHandler } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { fetchGraph } from "./api";
import type { GraphPayload, MapNodeInfo, PortalEdgeInfo } from "./api";
import { layoutGraph, nodeBox } from "./layout";
import { MapNode } from "./MapNode";
import type { MapFlowNode, PortalMarker } from "./MapNode";
import { SidePanel } from "./SidePanel";
import type { Selection } from "./SidePanel";

const nodeTypes = { map: MapNode };

function nodeBadges(info: MapNodeInfo): string[] {
  const badges: string[] = [];
  if (info.has_inn) badges.push("🛏");
  if (info.has_shop) badges.push("🛒");
  if (info.has_apothecary) badges.push("⚗");
  if (info.has_magic_core_shop) badges.push("💠");
  if (info.encounter) badges.push("⚔");
  return badges;
}

function buildFlowNodes(
  graph: GraphPayload,
  visible: (info: MapNodeInfo) => boolean,
): MapFlowNode[] {
  const nodes = graph.nodes.filter(visible);
  const visibleIds = new Set(nodes.map((n) => n.map_id));
  const edges = graph.edges.filter(
    (e) => visibleIds.has(e.source) && visibleIds.has(e.target),
  );
  const positions = layoutGraph(nodes, edges);

  const markersByMap = new Map<string, PortalMarker[]>();
  for (const edge of graph.edges) {
    const info = graph.nodes.find((n) => n.map_id === edge.source);
    if (!info) continue;
    const [mapW, mapH] = info.map_size_px;
    if (mapW <= 0 || mapH <= 0) continue;
    const [x, y, w, h] = edge.source_rect_px;
    const list = markersByMap.get(edge.source) ?? [];
    list.push({
      edgeId: edge.id,
      targetMap: edge.target,
      fx: (x + w / 2) / mapW,
      fy: (y + h / 2) / mapH,
    });
    markersByMap.set(edge.source, list);
  }

  return nodes.map((info) => {
    const box = nodeBox(info);
    const pos = positions.get(info.map_id) ?? { x: 0, y: 0 };
    return {
      id: info.map_id,
      type: "map" as const,
      position: pos,
      data: {
        mapId: info.map_id,
        displayName: info.display_name,
        isWorld: info.is_world,
        thumbWidth: box.thumbWidth,
        thumbHeight: box.thumbHeight,
        markers: markersByMap.get(info.map_id) ?? [],
        badges: nodeBadges(info),
      },
    };
  });
}

function buildFlowEdges(
  graph: GraphPayload,
  visibleIds: Set<string>,
): Edge[] {
  return graph.edges
    .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
    .map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
      label: `→ ${edge.target_tile[0]},${edge.target_tile[1]}`,
      labelShowBg: true,
    }));
}

export default function App() {
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [worldOnly, setWorldOnly] = useState(false);
  const [selection, setSelection] = useState<Selection>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<MapFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    fetchGraph().then(setGraph).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!graph) return;
    const visible = (info: MapNodeInfo) => !worldOnly || info.is_world;
    const flowNodes = buildFlowNodes(graph, visible);
    setNodes(flowNodes);
    setEdges(buildFlowEdges(graph, new Set(flowNodes.map((n) => n.id))));
  }, [graph, worldOnly, setNodes, setEdges]);

  const nodesById = useMemo(
    () => new Map((graph?.nodes ?? []).map((n) => [n.map_id, n])),
    [graph],
  );
  const edgesById = useMemo(
    () => new Map<string, PortalEdgeInfo>((graph?.edges ?? []).map((e) => [e.id, e])),
    [graph],
  );

  const onNodeClick: NodeMouseHandler = useCallback(
    (_evt, node) => setSelection({ kind: "node", id: node.id }),
    [],
  );
  const onEdgeClick: EdgeMouseHandler = useCallback(
    (_evt, edge) => setSelection({ kind: "edge", id: edge.id }),
    [],
  );
  const onPaneClick = useCallback(() => setSelection(null), []);
  const selectMap = useCallback(
    (mapId: string) => setSelection({ kind: "node", id: mapId }),
    [],
  );

  if (error) {
    return (
      <div className="fatal-error">
        <h2>Failed to load graph</h2>
        <p>{error}</p>
        <p>
          Is the backend running? <code>python -m tools.map_editor --web
          --scenario ./rusted_kingdoms</code>
        </p>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="title">Map Graph</span>
        <span className="counts">
          {nodes.length}/{graph?.nodes.length ?? 0} maps ·{" "}
          {edges.length}/{graph?.edges.length ?? 0} portals
        </span>
        <label className="toggle">
          <input
            type="checkbox"
            checked={worldOnly}
            onChange={(e) => setWorldOnly(e.target.checked)}
          />
          world maps only
        </label>
      </header>
      <div className="main-row">
        <div className="flow-wrap">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            fitView
            minZoom={0.05}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={24} />
            <Controls />
            <MiniMap pannable zoomable nodeStrokeWidth={3} />
          </ReactFlow>
        </div>
        <SidePanel
          selection={selection}
          nodesById={nodesById}
          edgesById={edgesById}
          onSelectMap={selectMap}
        />
      </div>
    </div>
  );
}
