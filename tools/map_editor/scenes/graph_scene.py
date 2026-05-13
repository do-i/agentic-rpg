"""Graph view of the scenario: nodes (maps with thumbnails) and edges (portals).

Interactions:
  - Left click on a node: open that map's detail view.
  - Left drag on a node: move it around.
  - Middle drag / right drag on background: pan the camera.
  - Mouse wheel: zoom the camera.
  - '0': reset camera to fit-all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pygame

from engine.common.scene.scene import Scene
from tools.map_editor.graph.portal_graph import GraphEdge, GraphNode, PortalGraph
from tools.map_editor.graph.spring_layout import spring_layout
from tools.map_editor.graph.thumbnails import ThumbnailCache


NODE_BG = (28, 28, 36)
NODE_BORDER = (90, 90, 110)
NODE_BORDER_HOVER = (240, 220, 120)
EDGE_COLOR = (110, 130, 160)
EDGE_COLOR_HIGHLIGHT = (240, 220, 120)
ARROW_SIZE = 10
NODE_PADDING = 8       # px of padding around the thumbnail inside a node
LABEL_HEIGHT = 18
CLICK_PIXEL_THRESHOLD = 4  # drag distance below this counts as a click


@dataclass
class _NodeView:
    node: GraphNode
    layout_x: float       # graph-space coordinates (from spring layout)
    layout_y: float
    width: int            # screen-space, derived from thumbnail
    height: int


class GraphScene(Scene):
    def __init__(
        self,
        graph: PortalGraph,
        thumbnails: ThumbnailCache,
        on_open_map: Callable[[GraphNode], None],
        font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> None:
        self._graph = graph
        self._thumbnails = thumbnails
        self._on_open_map = on_open_map
        self._font = font
        self._small_font = small_font

        layout = spring_layout(
            node_ids=[n.map_id for n in graph.nodes],
            edges=[(e.source, e.target) for e in graph.edges],
        )
        self._node_views: dict[str, _NodeView] = {}
        for n in graph.nodes:
            thumb = self._thumbnails.get(n.tmx_path)
            tw = thumb.get_width() if thumb else 96
            th = thumb.get_height() if thumb else 64
            x, y = layout.get(n.map_id, (500.0, 350.0))
            self._node_views[n.map_id] = _NodeView(
                node=n,
                layout_x=x,
                layout_y=y,
                width=tw + NODE_PADDING * 2,
                height=th + NODE_PADDING * 2 + LABEL_HEIGHT,
            )

        self._cam_x = 0.0
        self._cam_y = 0.0
        self._zoom = 1.0
        self._needs_fit = True

        self._hover_id: str | None = None
        self._drag_node_id: str | None = None
        self._drag_started_at: tuple[int, int] | None = None
        self._drag_total_pixels = 0
        self._panning = False
        self._last_mouse: tuple[int, int] | None = None

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
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_0, pygame.K_KP_0):
                self._needs_fit = True

    def _on_mouse_down(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            hit = self._node_at_screen(event.pos)
            if hit is not None:
                self._drag_node_id = hit
                self._drag_started_at = event.pos
                self._drag_total_pixels = 0
            else:
                self._panning = True
                self._last_mouse = event.pos
        elif event.button in (2, 3):
            self._panning = True
            self._last_mouse = event.pos

    def _on_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            if self._drag_node_id is not None and self._drag_total_pixels <= CLICK_PIXEL_THRESHOLD:
                node = self._graph.nodes_by_id[self._drag_node_id]
                self._drag_node_id = None
                self._drag_started_at = None
                self._on_open_map(node)
                return
            self._drag_node_id = None
            self._drag_started_at = None
        if event.button in (1, 2, 3):
            self._panning = False
            self._last_mouse = None

    def _on_mouse_motion(self, event: pygame.event.Event) -> None:
        self._hover_id = self._node_at_screen(event.pos)
        if self._drag_node_id is not None:
            dx_screen, dy_screen = event.rel
            self._drag_total_pixels += abs(dx_screen) + abs(dy_screen)
            view = self._node_views[self._drag_node_id]
            view.layout_x += dx_screen / self._zoom
            view.layout_y += dy_screen / self._zoom
        elif self._panning and self._last_mouse is not None:
            dx, dy = event.rel
            self._cam_x -= dx / self._zoom
            self._cam_y -= dy / self._zoom
            self._last_mouse = event.pos

    def _on_wheel(self, event: pygame.event.Event) -> None:
        if event.y == 0:
            return
        factor = 1.15 if event.y > 0 else 1.0 / 1.15
        self._zoom = max(0.25, min(2.5, self._zoom * factor))

    # ── render ───────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if self._needs_fit:
            self._fit_to_screen(screen.get_size())
            self._needs_fit = False

        screen.fill((14, 14, 20))
        self._render_edges(screen)
        for view in self._node_views.values():
            self._render_node(screen, view)
        self._render_hud(screen)

    def _render_edges(self, screen: pygame.Surface) -> None:
        for edge in self._graph.edges:
            src = self._node_views.get(edge.source)
            dst = self._node_views.get(edge.target)
            if src is None or dst is None:
                continue
            highlight = self._hover_id in (edge.source, edge.target)
            color = EDGE_COLOR_HIGHLIGHT if highlight else EDGE_COLOR
            sx, sy = self._layout_to_screen(src.layout_x, src.layout_y)
            tx, ty = self._layout_to_screen(dst.layout_x, dst.layout_y)
            pygame.draw.line(screen, color, (sx, sy), (tx, ty), 2 if highlight else 1)
            self._draw_arrowhead(screen, sx, sy, tx, ty, color)

    def _draw_arrowhead(
        self, screen: pygame.Surface, sx: int, sy: int, tx: int, ty: int, color
    ) -> None:
        angle = math.atan2(ty - sy, tx - sx)
        # Pull the arrow back so it sits before the target's center, not on it.
        back = 40
        bx = tx - math.cos(angle) * back
        by = ty - math.sin(angle) * back
        left = (
            bx - math.cos(angle - 0.4) * ARROW_SIZE,
            by - math.sin(angle - 0.4) * ARROW_SIZE,
        )
        right = (
            bx - math.cos(angle + 0.4) * ARROW_SIZE,
            by - math.sin(angle + 0.4) * ARROW_SIZE,
        )
        pygame.draw.polygon(screen, color, [(bx, by), left, right])

    def _render_node(self, screen: pygame.Surface, view: _NodeView) -> None:
        cx, cy = self._layout_to_screen(view.layout_x, view.layout_y)
        w = int(view.width * self._zoom)
        h = int(view.height * self._zoom)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

        if rect.right < 0 or rect.bottom < 0 or rect.left > screen.get_width() or rect.top > screen.get_height():
            return

        is_hover = self._hover_id == view.node.map_id
        pygame.draw.rect(screen, NODE_BG, rect)
        pygame.draw.rect(
            screen,
            NODE_BORDER_HOVER if is_hover else NODE_BORDER,
            rect,
            width=2 if is_hover else 1,
        )

        thumb = self._thumbnails.get(view.node.tmx_path)
        if thumb is not None:
            scaled = pygame.transform.scale(
                thumb, (int(thumb.get_width() * self._zoom), int(thumb.get_height() * self._zoom))
            )
            screen.blit(
                scaled,
                (rect.x + int(NODE_PADDING * self._zoom), rect.y + int(NODE_PADDING * self._zoom)),
            )

        label = self._small_font.render(view.node.display_name, True, (230, 230, 230))
        screen.blit(
            label,
            (rect.x + 6, rect.bottom - int(LABEL_HEIGHT * self._zoom) - 2),
        )

    def _render_hud(self, screen: pygame.Surface) -> None:
        hud = self._font.render(
            f"Map Graph   nodes={len(self._graph.nodes)}  edges={len(self._graph.edges)}   "
            f"zoom={self._zoom:.2f}   [click=open, drag node=move, drag bg=pan, wheel=zoom, 0=fit]",
            True,
            (220, 220, 220),
        )
        bg = pygame.Surface((hud.get_width() + 12, hud.get_height() + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (8, 8))
        screen.blit(hud, (14, 11))

    # ── geometry helpers ─────────────────────────────────────────────────

    def _layout_to_screen(self, lx: float, ly: float) -> tuple[int, int]:
        return (
            int((lx - self._cam_x) * self._zoom),
            int((ly - self._cam_y) * self._zoom),
        )

    def _node_at_screen(self, pos: tuple[int, int]) -> str | None:
        # Reverse order so visually-on-top (last-drawn) wins.
        for view in reversed(list(self._node_views.values())):
            cx, cy = self._layout_to_screen(view.layout_x, view.layout_y)
            w = int(view.width * self._zoom)
            h = int(view.height * self._zoom)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            if rect.collidepoint(pos):
                return view.node.map_id
        return None

    def _fit_to_screen(self, screen_size: tuple[int, int]) -> None:
        if not self._node_views:
            return
        min_x = min(v.layout_x - v.width / 2 for v in self._node_views.values())
        max_x = max(v.layout_x + v.width / 2 for v in self._node_views.values())
        min_y = min(v.layout_y - v.height / 2 for v in self._node_views.values())
        max_y = max(v.layout_y + v.height / 2 for v in self._node_views.values())
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        margin = 80
        zx = (screen_size[0] - margin * 2) / span_x
        zy = (screen_size[1] - margin * 2) / span_y
        self._zoom = max(0.25, min(2.0, min(zx, zy)))
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self._cam_x = center_x - (screen_size[0] / 2) / self._zoom
        self._cam_y = center_y - (screen_size[1] / 2) / self._zoom
