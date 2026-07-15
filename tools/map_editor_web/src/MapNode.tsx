// Custom React Flow node: map thumbnail + portal-tile markers + label.
//
// The whole node is a connection target; the small "+" dot on the right edge
// is the drag-source for creating a new portal (drag it onto another map).

import { Handle, Position } from "@xyflow/react";
import type { NodeProps, Node } from "@xyflow/react";
import { thumbnailUrl } from "./api";

export interface PortalMarker {
  edgeId: string;
  targetMap: string;
  // Center of the portal rect, in thumbnail-relative fractions [0..1].
  fx: number;
  fy: number;
}

export interface MapNodeData extends Record<string, unknown> {
  mapId: string;
  displayName: string;
  isWorld: boolean;
  thumbWidth: number;
  thumbHeight: number;
  markers: PortalMarker[];
  badges: string[];
}

export type MapFlowNode = Node<MapNodeData, "map">;

export function MapNode({ data, selected }: NodeProps<MapFlowNode>) {
  return (
    <div
      className={`map-node${selected ? " selected" : ""}${
        data.isWorld ? "" : " interior"
      }`}
      style={{ width: data.thumbWidth }}
    >
      <div
        className="thumb-wrap"
        style={{ width: data.thumbWidth, height: data.thumbHeight }}
      >
        <img
          src={thumbnailUrl(data.mapId)}
          alt={data.mapId}
          draggable={false}
          width={data.thumbWidth}
          height={data.thumbHeight}
        />
        {data.markers.map((m) => (
          <div
            key={`${m.edgeId}:${m.fx}:${m.fy}`}
            className="portal-marker"
            title={`portal → ${m.targetMap}`}
            style={{
              left: `${m.fx * 100}%`,
              top: `${m.fy * 100}%`,
            }}
          />
        ))}
      </div>
      <div className="map-node-label">
        <span className="name">{data.displayName}</span>
        {data.badges.length > 0 && (
          <span className="badges">{data.badges.join(" ")}</span>
        )}
      </div>
      <Handle type="target" position={Position.Left} className="target-handle" />
      <Handle
        type="source"
        position={Position.Right}
        className="source-handle"
        title="Drag onto another map to create a portal"
      />
    </div>
  );
}
