"""Fruchterman-Reingold force-directed layout, kept deliberately small.

Returns {node_id: (x, y)} in a unit-ish coordinate space; the renderer is
responsible for fitting to its viewport. Deterministic when given a seed.
"""

from __future__ import annotations

import math
import random


def spring_layout(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    iterations: int = 250,
    seed: int = 1,
    width: float = 1000.0,
    height: float = 700.0,
) -> dict[str, tuple[float, float]]:
    rng = random.Random(seed)
    if not node_ids:
        return {}

    # Initial random placement inside the rectangle.
    pos: dict[str, list[float]] = {
        nid: [rng.uniform(0, width), rng.uniform(0, height)] for nid in node_ids
    }

    # FR's ideal edge length: k = sqrt(area / N). Repulsion ~ k^2/d, attraction ~ d^2/k.
    area = width * height
    k = math.sqrt(area / max(1, len(node_ids)))
    # Temperature cools linearly each step so motion damps out.
    t = width / 10.0
    dt = t / max(1, iterations)

    # Deduplicate undirected pairs so an A↔B portal pair doesn't pull twice.
    edge_pairs = {frozenset((s, t)) for s, t in edges if s != t and s in pos and t in pos}
    edge_list = [tuple(p) for p in edge_pairs]

    for _ in range(iterations):
        disp: dict[str, list[float]] = {nid: [0.0, 0.0] for nid in node_ids}

        # Repulsion between all pairs.
        for i, a in enumerate(node_ids):
            ax, ay = pos[a]
            for b in node_ids[i + 1 :]:
                bx, by = pos[b]
                dx = ax - bx
                dy = ay - by
                dist = math.hypot(dx, dy) or 0.01
                force = (k * k) / dist
                ux = dx / dist
                uy = dy / dist
                disp[a][0] += ux * force
                disp[a][1] += uy * force
                disp[b][0] -= ux * force
                disp[b][1] -= uy * force

        # Attraction along edges.
        for a, b in edge_list:
            ax, ay = pos[a]
            bx, by = pos[b]
            dx = ax - bx
            dy = ay - by
            dist = math.hypot(dx, dy) or 0.01
            force = (dist * dist) / k
            ux = dx / dist
            uy = dy / dist
            disp[a][0] -= ux * force
            disp[a][1] -= uy * force
            disp[b][0] += ux * force
            disp[b][1] += uy * force

        # Apply displacement, capped by temperature, then keep inside bounds.
        for nid in node_ids:
            dx, dy = disp[nid]
            d = math.hypot(dx, dy) or 0.01
            step = min(d, t)
            pos[nid][0] += (dx / d) * step
            pos[nid][1] += (dy / d) * step
            pos[nid][0] = min(width, max(0.0, pos[nid][0]))
            pos[nid][1] = min(height, max(0.0, pos[nid][1]))

        t = max(0.1, t - dt)

    return {nid: (xy[0], xy[1]) for nid, xy in pos.items()}
