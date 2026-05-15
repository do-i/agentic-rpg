"""Fruchterman-Reingold force-directed layout, kept deliberately small.

Nodes are rectangles of varying size (map thumbnails), so the layout is
size-aware: repulsion and edge length scale with each node's extent, and a
final separation pass guarantees no two node rectangles overlap. Returns
{node_id: (x, y)} centre positions; the renderer fits to its viewport.
Deterministic when given a seed.
"""

from __future__ import annotations

import math
import random


def spring_layout(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    sizes: dict[str, tuple[float, float]],
    iterations: int = 400,
    seed: int = 1,
) -> dict[str, tuple[float, float]]:
    rng = random.Random(seed)
    if not node_ids:
        return {}

    # Each node's "radius" is half its bounding-box diagonal; layout spacing
    # is driven by these so large thumbnails don't pile on top of each other.
    radius = {nid: 0.5 * math.hypot(*sizes[nid]) for nid in node_ids}
    avg_r = sum(radius.values()) / len(radius)

    # Canvas scales with node count and node size so there is room to spread.
    span = max(800.0, avg_r * 6.0 * math.sqrt(len(node_ids)))
    pos: dict[str, list[float]] = {
        nid: [rng.uniform(0, span), rng.uniform(0, span)] for nid in node_ids
    }

    # Ideal gap between rectangle edges; also the breathing room on edges.
    k = avg_r * 2.5
    t = span / 8.0
    dt = t / max(1, iterations)

    # Deduplicate undirected pairs so an A↔B portal pair doesn't pull twice.
    edge_pairs = {frozenset((s, e)) for s, e in edges if s != e and s in pos and e in pos}
    edge_list = [tuple(p) for p in edge_pairs]

    for _ in range(iterations):
        disp: dict[str, list[float]] = {nid: [0.0, 0.0] for nid in node_ids}

        # Repulsion between all pairs, measured edge-to-edge (gap) rather than
        # centre-to-centre so big and small nodes are spaced consistently.
        for i, a in enumerate(node_ids):
            ax, ay = pos[a]
            for b in node_ids[i + 1:]:
                bx, by = pos[b]
                dx = ax - bx
                dy = ay - by
                dist = math.hypot(dx, dy) or 0.01
                gap = dist - radius[a] - radius[b]
                if gap >= k:
                    continue
                force = (k * k) / max(gap + k, 0.01)
                if gap < 0:
                    force += k * (-gap)  # extra shove to break overlap
                ux, uy = dx / dist, dy / dist
                disp[a][0] += ux * force
                disp[a][1] += uy * force
                disp[b][0] -= ux * force
                disp[b][1] -= uy * force

        # Attraction along edges toward an ideal centre distance that leaves
        # both rectangles plus one k of clearance between them.
        for a, b in edge_list:
            ax, ay = pos[a]
            bx, by = pos[b]
            dx = ax - bx
            dy = ay - by
            dist = math.hypot(dx, dy) or 0.01
            ideal = radius[a] + radius[b] + k
            force = ((dist - ideal) * abs(dist - ideal)) / k
            ux, uy = dx / dist, dy / dist
            disp[a][0] -= ux * force
            disp[a][1] -= uy * force
            disp[b][0] += ux * force
            disp[b][1] += uy * force

        # Apply displacement, capped by the cooling temperature.
        for nid in node_ids:
            dx, dy = disp[nid]
            d = math.hypot(dx, dy) or 0.01
            step = min(d, t)
            pos[nid][0] += (dx / d) * step
            pos[nid][1] += (dy / d) * step

        t = max(0.1, t - dt)

    _separate_overlaps(node_ids, pos, sizes)

    return {nid: (xy[0], xy[1]) for nid, xy in pos.items()}


def _separate_overlaps(
    node_ids: list[str],
    pos: dict[str, list[float]],
    sizes: dict[str, tuple[float, float]],
    margin: float = 28.0,
    passes: int = 80,
) -> None:
    """Iteratively push apart any pair of overlapping node rectangles.

    Resolves along the axis of least penetration (AABB style), splitting the
    correction between the two nodes. Converges to a layout with at least
    `margin` pixels of clear space between every pair of rectangles.
    """
    for _ in range(passes):
        moved = False
        for i, a in enumerate(node_ids):
            aw, ah = sizes[a]
            for b in node_ids[i + 1:]:
                bw, bh = sizes[b]
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                min_x = (aw + bw) / 2 + margin
                min_y = (ah + bh) / 2 + margin
                overlap_x = min_x - abs(dx)
                overlap_y = min_y - abs(dy)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                if overlap_x < overlap_y:
                    shift = overlap_x / 2
                    sign = 1.0 if dx >= 0 else -1.0
                    pos[a][0] += sign * shift
                    pos[b][0] -= sign * shift
                else:
                    shift = overlap_y / 2
                    sign = 1.0 if dy >= 0 else -1.0
                    pos[a][1] += sign * shift
                    pos[b][1] -= sign * shift
                moved = True
        if not moved:
            break
