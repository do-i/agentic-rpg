import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import type {
  Connection,
  Edge,
  EdgeMouseHandler,
  NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { fetchGraph } from "./api";
import type {
  CreatePortalRequest,
  GraphPayload,
  MapNodeInfo,
  PortalEdgeInfo,
} from "./api";
import { layoutGraph, nodeBox } from "./layout";
import { MapNode } from "./MapNode";
import type { MapFlowNode, PortalMarker } from "./MapNode";
import { applyOp, OpStack } from "./ops";
import { PortalDialog, RetargetDialog } from "./PortalDialog";
import { SidePanel } from "./SidePanel";
import type { Selection } from "./SidePanel";

const nodeTypes = { map: MapNode };
const TOAST_MS = 3200;

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
  positions: Map<string, { x: number; y: number }>,
): MapFlowNode[] {
  const nodes = graph.nodes.filter(visible);

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

function buildFlowEdges(graph: GraphPayload, visibleIds: Set<string>): Edge[] {
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
  const [connectDraft, setConnectDraft] = useState<{
    source: string;
    target: string;
  } | null>(null);
  const [retargetEdge, setRetargetEdge] = useState<PortalEdgeInfo | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const opStack = useRef(new OpStack());
  const toastTimer = useRef<number | undefined>(undefined);
  // Positions survive refetches so the layout doesn't jump after each edit;
  // user drags are folded in via onNodesChange before every re-layout.
  const positionsRef = useRef(new Map<string, { x: number; y: number }>());

  const showToast = useCallback((text: string) => {
    setToast(text);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), TOAST_MS);
  }, []);

  const refresh = useCallback(async () => {
    try {
      setGraph(await fetchGraph());
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!graph) return;
    const visible = (info: MapNodeInfo) => !worldOnly || info.is_world;
    const visibleNodes = graph.nodes.filter(visible);
    const visibleIds = new Set(visibleNodes.map((n) => n.map_id));
    // Layout only maps that don't have a position yet (first load, or maps
    // revealed by toggling the world filter).
    const missing = visibleNodes.filter(
      (n) => !positionsRef.current.has(n.map_id),
    );
    if (missing.length > 0) {
      const fresh = layoutGraph(
        visibleNodes,
        graph.edges.filter(
          (e) => visibleIds.has(e.source) && visibleIds.has(e.target),
        ),
      );
      for (const [id, pos] of fresh) {
        if (!positionsRef.current.has(id)) positionsRef.current.set(id, pos);
      }
    }
    setNodes(buildFlowNodes(graph, visible, positionsRef.current));
    setEdges(buildFlowEdges(graph, visibleIds));
  }, [graph, worldOnly, setNodes, setEdges]);

  // Keep the position cache in sync with user drags.
  const handleNodesChange: typeof onNodesChange = useCallback(
    (changes) => {
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          positionsRef.current.set(change.id, change.position);
        }
      }
      onNodesChange(changes);
    },
    [onNodesChange],
  );

  const nodesById = useMemo(
    () => new Map((graph?.nodes ?? []).map((n) => [n.map_id, n])),
    [graph],
  );
  const edgesById = useMemo(
    () =>
      new Map<string, PortalEdgeInfo>(
        (graph?.edges ?? []).map((e) => [e.id, e]),
      ),
    [graph],
  );

  const runMutation = useCallback(
    async (action: () => Promise<string>) => {
      try {
        const message = await action();
        setHistoryVersion((v) => v + 1);
        await refresh();
        showToast(message);
      } catch (e) {
        showToast(`Error: ${e instanceof Error ? e.message : String(e)}`);
      }
    },
    [refresh, showToast],
  );

  const onConnect = useCallback((conn: Connection) => {
    if (conn.source && conn.target && conn.source !== conn.target) {
      setConnectDraft({ source: conn.source, target: conn.target });
    }
  }, []);

  const createFromDialog = useCallback(
    (request: CreatePortalRequest, reciprocal: CreatePortalRequest | null) => {
      setConnectDraft(null);
      runMutation(async () => {
        const op = {
          kind: "create" as const,
          requests: reciprocal ? [request, reciprocal] : [request],
          createdIds: [],
          label: `create ${request.source_map} → ${request.target_map}`,
        };
        await applyOp(op);
        opStack.current.push(op);
        return `Created portal ${request.source_map} → ${request.target_map}${
          reciprocal ? " (+ return portal)" : ""
        }`;
      });
    },
    [runMutation],
  );

  const retargetFromDialog = useCallback(
    (tile: [number, number]) => {
      const edge = retargetEdge;
      setRetargetEdge(null);
      if (!edge) return;
      runMutation(async () => {
        const op = {
          kind: "retarget" as const,
          sourceMap: edge.source,
          objId: edge.portal_obj_id,
          before: {
            target_map: edge.target,
            target_tile: edge.target_tile,
            source_rect_px: null,
          },
          after: {
            target_map: edge.target,
            target_tile: tile,
            source_rect_px: null,
          },
          label: `move arrival of ${edge.id}`,
        };
        await applyOp(op);
        opStack.current.push(op);
        return `Moved arrival to ${tile[0]},${tile[1]}`;
      });
    },
    [retargetEdge, runMutation],
  );

  const deleteEdge = useCallback(
    (edge: PortalEdgeInfo) => {
      if (
        !window.confirm(
          `Delete portal ${edge.source} → ${edge.target} (object #${edge.portal_obj_id})?`,
        )
      ) {
        return;
      }
      setSelection(null);
      runMutation(async () => {
        const op = {
          kind: "delete" as const,
          edge,
          label: `delete ${edge.id}`,
        };
        await applyOp(op);
        opStack.current.push(op);
        return `Deleted portal ${edge.source} → ${edge.target}`;
      });
    },
    [runMutation],
  );

  const undo = useCallback(() => {
    setSelection(null);
    runMutation(async () => {
      const label = await opStack.current.undo();
      return label ? `Undid: ${label}` : "Nothing to undo";
    });
  }, [runMutation]);

  const redo = useCallback(() => {
    setSelection(null);
    runMutation(async () => {
      const label = await opStack.current.redo();
      return label ? `Redid: ${label}` : "Nothing to redo";
    });
  }, [runMutation]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if (e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo]);

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

  const draftSource = connectDraft ? nodesById.get(connectDraft.source) : null;
  const draftTarget = connectDraft ? nodesById.get(connectDraft.target) : null;
  const retargetTargetMap = retargetEdge
    ? nodesById.get(retargetEdge.target)
    : null;
  void historyVersion; // re-render trigger for canUndo/canRedo

  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="title">Map Graph</span>
        <span className="counts">
          {nodes.length}/{graph?.nodes.length ?? 0} maps · {edges.length}/
          {graph?.edges.length ?? 0} portals
        </span>
        <button
          onClick={undo}
          disabled={!opStack.current.canUndo}
          title="Ctrl+Z"
        >
          ⌫ undo
        </button>
        <button
          onClick={redo}
          disabled={!opStack.current.canRedo}
          title="Ctrl+Shift+Z"
        >
          redo ⌦
        </button>
        <span className="hint dim">
          drag the green dot between maps to link them · edits write TMX
          immediately (.bak kept)
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
            onNodesChange={handleNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
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
          onRetargetEdge={setRetargetEdge}
          onDeleteEdge={deleteEdge}
        />
      </div>
      {connectDraft && draftSource && draftTarget && (
        <PortalDialog
          source={draftSource}
          target={draftTarget}
          allEdges={graph?.edges ?? []}
          onCancel={() => setConnectDraft(null)}
          onCreate={createFromDialog}
        />
      )}
      {retargetEdge && retargetTargetMap && (
        <RetargetDialog
          edge={retargetEdge}
          target={retargetTargetMap}
          allEdges={graph?.edges ?? []}
          onCancel={() => setRetargetEdge(null)}
          onRetarget={retargetFromDialog}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
