"""Graph view of the scenario: nodes (maps with thumbnails) and edges (portals).

Interactions:
  - Click node: select node (details show in right panel).
  - Click portal edge: select edge.
  - Click empty: deselect.
  - Drag node: move it around (click vs. drag distinguished by motion threshold).
  - Drag background: pan camera.
  - Mouse wheel: zoom camera.
  - Enter: open selected node in detail viewer.
  - 0: refit camera to all nodes.
  - Esc: deselect.

Each portal is its own directed edge anchored to the portal's source tile on
the source map's thumbnail and the destination tile on the target map's
thumbnail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Union

import pygame

from engine.common.scene.scene import Scene
from tools.map_editor.graph.portal_graph import GraphEdge, GraphNode, PortalGraph
from tools.map_editor.graph.spring_layout import spring_layout
from tools.map_editor.graph.thumbnails import ThumbnailCache
from tools.map_editor.scenes.side_panel import PANEL_WIDTH, render_side_panel


NODE_BG = (28, 28, 36)
NODE_BORDER = (90, 90, 110)
NODE_BORDER_HOVER = (180, 180, 200)
NODE_BORDER_SELECTED = (240, 220, 120)
EDGE_COLOR = (110, 130, 160)
EDGE_COLOR_HOVER = (180, 200, 230)
EDGE_COLOR_SELECTED = (240, 220, 120)
ARROW_SIZE = 10
NODE_PADDING = 8
LABEL_HEIGHT = 18
CLICK_PIXEL_THRESHOLD = 4
EDGE_PICK_THRESHOLD_PX = 8


Selection = Union[GraphNode, GraphEdge, None]


@dataclass
class _NodeView:
    node: GraphNode
    layout_x: float
    layout_y: float
    width: int
    height: int


class GraphScene(Scene):
    def __init__(
        self,
        graph: PortalGraph,
        thumbnails: ThumbnailCache,
        on_open_map: Callable[[GraphNode], None],
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        header_font: pygame.font.Font,
    ) -> None:
        self._graph = graph
        self._thumbnails = thumbnails
        self._on_open_map = on_open_map
        self._font = font
        self._small_font = small_font
        self._header_font = header_font

        layout = spring_layout(
            node_ids=[n.map_id for n in graph.nodes],
            edges=[(e.source, e.target) for e in graph.edges],
        )
        self._node_views: dict[str, _NodeView] = {}
        for node in graph.nodes:
            thumb = thumbnails.get(node.tmx_path)
            if thumb is not None:
                w = thumb.get_width() + NODE_PADDING * 2
                h = thumb.get_height() + NODE_PADDING * 2 + LABEL_HEIGHT
            else:
                w, h = 180, 120
            lx, ly = layout.get(node.map_id, (0.0, 0.0))
            self._node_views[node.map_id] = _NodeView(
                node=node, layout_x=lx, layout_y=ly, width=w, height=h
            )

        self._cam_x = 0.0
        self._cam_y = 0.0
        self._zoom = 1.0
        self._needs_fit = True

        self._hover_node: str | None = None
        self._hover_edge_idx: int | None = None
        self._selection: Selection = None

        self._drag_node_id: str | None = None
        self._drag_total_pixels = 0
        self._panning = False
        self._last_mouse: tuple[int, int] | None = None

        self._panel_rect: pygame.Rect | None = None

    # ── input ────────────────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._on_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._on_mouse_up(event)
            elif event.type == pygame.MOUSEMOTION:
                self._on_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._on_wheel(event)
            elif event.type == pygame.KEYDOWN:
                self._on_key_down(event)

    def _on_mouse_down(self, event: pygame.event.Event) -> None:
        if self._in_panel(event.pos):
            return
        if event.button == 1:
            hit_node = self._node_at_screen(event.pos)
            if hit_node is not None:
                self._drag_node_id = hit_node
                self._drag_total_pixels = 0
                return
            hit_edge_idx = self._edge_at_screen(event.pos)
            if hit_edge_idx is not None:
                self._selection = self._graph.edges[hit_edge_idx]
                return
            self._panning = True
            self._last_mouse = event.pos
            self._selection = None
        elif event.button in (2, 3):
            self._panning = True
            self._last_mouse = event.pos

    def _on_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1 and self._drag_node_id is not None:
            if self._drag_total_pixels <= CLICK_PIXEL_THRESHOLD:
                self._selection = self._graph.nodes_by_id[self._drag_node_id]
            self._drag_node_id = None
        if event.button in (1, 2, 3):
            self._panning = False
            self._last_mouse = None

    def _on_mouse_motion(self, event: pygame.event.Event) -> None:
        if self._in_panel(event.pos):
            self._hover_node = None
            self._hover_edge_idx = None
        else:
            self._hover_node = self._node_at_screen(event.pos)
            self._hover_edge_idx = (
                self._edge_at_screen(event.pos) if self._hover_node is None else None
            )

        if self._drag_node_id is not None:
            dx, dy = event.rel
            self._drag_total_pixels += abs(dx) + abs(dy)
            view = self._node_views[self._drag_node_id]
            view.layout_x += dx / self._zoom
            view.layout_y += dy / self._zoom
        elif self._panning and self._last_mouse is not None:
            dx, dy = event.rel
            self._cam_x -= dx / self._zoom
            self._cam_y -= dy / self._zoom
            self._last_mouse = event.pos

    def _on_wheel(self, event: pygame.event.Event) -> None:
        factor = 1.15 if event.y > 0 else 1.0 / 1.15
        self._zoom = max(0.25, min(2.5, self._zoom * factor))

    def _on_key_down(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_0, pygame.K_KP_0):
            self._needs_fit = True
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if isinstance(self._selection, GraphNode):
                self._on_open_map(self._selection)
        elif event.key == pygame.K_ESCAPE:
            self._selection = None

    # ── render ───────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._needs_fit:
            self._fit_to_screen(self._graph_viewport(screen.get_size()))
            self._needs_fit = False

        screen.fill((14, 14, 20))
        self._render_edges(screen)
        for view in self._node_views.values():
            self._render_node(screen, view)
        self._render_hud(screen)

        self._panel_rect = render_side_panel(
            screen=screen,
            selection=self._selection,
            graph=self._graph,
            thumbnails=self._thumbnails,
            font=self._font,
            small_font=self._small_font,
            header_font=self._header_font,
        )

    def _render_edges(self, screen: pygame.Surface) -> None:
        for idx, edge in enumerate(self._graph.edges):
            endpoints = self._edge_endpoints(edge)
            if endpoints is None:
                continue
            (sx, sy), (tx, ty) = endpoints

            is_selected = self._selection is edge
            is_hover = self._hover_edge_idx == idx
            if is_selected:
                color, width = EDGE_COLOR_SELECTED, 3
            elif is_hover:
                color, width = EDGE_COLOR_HOVER, 2
            else:
                color, width = EDGE_COLOR, 1

            pygame.draw.line(screen, color, (sx, sy), (tx, ty), width)
            self._draw_arrowhead(screen, sx, sy, tx, ty, color)

    def _draw_arrowhead(
        self, screen: pygame.Surface, sx: int, sy: int, tx: int, ty: int, color
    ) -> None:
        dx, dy = tx - sx, ty - sy
        length = math.hypot(dx, dy)
        if length < 1.0:
            return
        angle = math.atan2(dy, dx)
        back = min(20, length * 0.4)
        bx = tx - math.cos(angle) * back
        by = ty - math.sin(angle) * back
        left = (
            bx + math.cos(angle + math.pi / 2) * ARROW_SIZE / 2,
            by + math.sin(angle + math.pi / 2) * ARROW_SIZE / 2,
        )
        right = (
            bx + math.cos(angle - math.pi / 2) * ARROW_SIZE / 2,
            by + math.sin(angle - math.pi / 2) * ARROW_SIZE / 2,
        )
        tip = (
            bx + math.cos(angle) * ARROW_SIZE,
            by + math.sin(angle) * ARROW_SIZE,
        )
        pygame.draw.polygon(screen, color, [tip, left, right])

    def _render_node(self, screen: pygame.Surface, view: _NodeView) -> None:
        cx, cy = self._layout_to_screen(view.layout_x, view.layout_y)
        w = int(view.width * self._zoom)
        h = int(view.height * self._zoom)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

        viewport = self._graph_viewport(screen.get_size())
        if (
            rect.right < viewport[0]
            or rect.bottom < viewport[1]
            or rect.left > viewport[0] + viewport[2]
            or rect.top > viewport[1] + viewport[3]
        ):
            return

        is_selected = (
            isinstance(self._selection, GraphNode)
            and self._selection.map_id == view.node.map_id
        )
        is_hover = self._hover_node == view.node.map_id

        pygame.draw.rect(screen, NODE_BG, rect)
        if is_selected:
            border, bw = NODE_BORDER_SELECTED, 3
        elif is_hover:
            border, bw = NODE_BORDER_HOVER, 2
        else:
            border, bw = NODE_BORDER, 1
        pygame.draw.rect(screen, border, rect, width=bw)

        thumb = self._thumbnails.get(view.node.tmx_path)
        if thumb is not None:
            scaled = pygame.transform.scale(
                thumb,
                (
                    int(thumb.get_width() * self._zoom),
                    int(thumb.get_height() * self._zoom),
                ),
            )
            screen.blit(
                scaled,
                (
                    rect.x + int(NODE_PADDING * self._zoom),
                    rect.y + int(NODE_PADDING * self._zoom),
                ),
            )

        label = self._small_font.render(view.node.display_name, True, (230, 230, 230))
        screen.blit(
            label,
            (rect.x + 6, rect.bottom - LABEL_HEIGHT * self._zoom - 2),
        )

    def _render_hud(self, screen: pygame.Surface) -> None:
        hud = self._font.render(
            f"Map Graph   nodes={len(self._graph.nodes)}  edges={len(self._graph.edges)}   "
            f"zoom={self._zoom:.2f}   "
            f"[click=select  drag=move  wheel=zoom  Enter=open  0=fit]",
            True,
            (220, 220, 220),
        )
        screen.blit(hud, (10, 10))

    def update(self, dt: float) -> None:
        return

    # ── geometry helpers ─────────────────────────────────────────────────

    def _graph_viewport(self, screen_size: tuple[int, int]) -> tuple[int, int, int, int]:
        return (0, 0, max(1, screen_size[0] - PANEL_WIDTH), screen_size[1])

    def _in_panel(self, pos: tuple[int, int]) -> bool:
        return self._panel_rect is not None and self._panel_rect.collidepoint(pos)

    def _layout_to_screen(self, lx: float, ly: float) -> tuple[int, int]:
        return (
            int((lx - self._cam_x) * self._zoom),
            int((ly - self._cam_y) * self._zoom),
        )

    def _node_at_screen(self, pos: tuple[int, int]) -> str | None:
        for view in reversed(list(self._node_views.values())):
            cx, cy = self._layout_to_screen(view.layout_x, view.layout_y)
            w = int(view.width * self._zoom)
            h = int(view.height * self._zoom)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            if rect.collidepoint(pos):
                return view.node.map_id
        return None

    def _edge_at_screen(self, pos: tuple[int, int]) -> int | None:
        best_idx: int | None = None
        best_dist = EDGE_PICK_THRESHOLD_PX
        for idx, edge in enumerate(self._graph.edges):
            endpoints = self._edge_endpoints(edge)
            if endpoints is None:
                continue
            (sx, sy), (tx, ty) = endpoints
            if (sx, sy) == (tx, ty):
                continue
            d = _distance_point_to_segment(pos, (sx, sy), (tx, ty))
            if d < best_dist:
                best_dist = d
                best_idx = idx
        return best_idx

    def _edge_endpoints(
        self, edge: GraphEdge
    ) -> tuple[tuple[int, int], tuple[int, int]] | None:
        src_view = self._node_views.get(edge.source)
        dst_view = self._node_views.get(edge.target)
        if src_view is None or dst_view is None:
            return None
        src_pt = self._portal_point_on_node(src_view, edge.source_tile)
        dst_pt = self._portal_point_on_node(dst_view, edge.target_tile)
        return src_pt, dst_pt

    def _portal_point_on_node(
        self, view: _NodeView, tile: tuple[int, int]
    ) -> tuple[int, int]:
        """Map a tile coord on this node's map to a screen point on its thumbnail.

        Falls back to the node center if thumbnail or map dims are unavailable.
        """
        cx, cy = self._layout_to_screen(view.layout_x, view.layout_y)
        thumb = self._thumbnails.get(view.node.tmx_path)
        map_w_px, map_h_px = view.node.map_size_px
        tile_w_px, tile_h_px = view.node.tile_size_px
        if thumb is None or map_w_px == 0 or map_h_px == 0:
            return cx, cy
        thumb_w, thumb_h = thumb.get_size()
        col, row = tile
        tx_thumb = (col + 0.5) * tile_w_px * (thumb_w / map_w_px)
        ty_thumb = (row + 0.5) * tile_h_px * (thumb_h / map_h_px)
        node_w = int(view.width * self._zoom)
        node_h = int(view.height * self._zoom)
        rect_x = cx - node_w // 2
        rect_y = cy - node_h // 2
        thumb_origin_x = rect_x + int(NODE_PADDING * self._zoom)
        thumb_origin_y = rect_y + int(NODE_PADDING * self._zoom)
        return (
            int(thumb_origin_x + tx_thumb * self._zoom),
            int(thumb_origin_y + ty_thumb * self._zoom),
        )

    def _fit_to_screen(self, viewport: tuple[int, int, int, int]) -> None:
        if not self._node_views:
            return
        min_x = min(v.layout_x - v.width / 2 for v in self._node_views.values())
        min_y = min(v.layout_y - v.height / 2 for v in self._node_views.values())
        max_x = max(v.layout_x + v.width / 2 for v in self._node_views.values())
        max_y = max(v.layout_y + v.height / 2 for v in self._node_views.values())
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        margin = 60
        vw, vh = viewport[2], viewport[3]
        zx = (vw - margin * 2) / span_x
        zy = (vh - margin * 2) / span_y
        self._zoom = max(0.25, min(2.0, min(zx, zy)))
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self._cam_x = center_x - (vw / 2) / self._zoom
        self._cam_y = center_y - (vh / 2) / self._zoom


def _distance_point_to_segment(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    length_sq = abx * abx + aby * aby
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / length_sq))
    proj_x = ax + t * abx
    proj_y = ay + t * aby
    return math.hypot(px - proj_x, py - proj_y)
