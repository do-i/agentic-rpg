"""Graph view of the scenario: nodes (maps with thumbnails) and edges (portals).

Interactions:
  - Click node: select node (details in right panel).
  - Click portal edge: select edge.
  - Click empty: deselect.
  - Drag node: move it around.
  - Drag background: pan camera.
  - Drag panel separator: resize the side panel.
  - Click a value in the side panel: copy to clipboard.
  - Mouse wheel: zoom camera.
  - Enter: open selected node in detail viewer.
  - 0: refit camera.
  - Esc: deselect.

Each portal is its own directed edge, anchored to the portal's source tile on
the source map's thumbnail and the destination tile on the target map's
thumbnail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Union

import pygame

from engine.common.scene.scene import Scene
from tools.map_editor.edit.editor_state import (
    EditorState,
    STEP_DEST_NODE,
    STEP_DEST_TILE,
    STEP_SOURCE_NODE,
    STEP_SOURCE_TILE,
)
from tools.map_editor.edit.tmx_writer import create_portal, save_portal_target
from tools.map_editor.graph.portal_graph import GraphEdge, GraphNode, PortalGraph
from tools.map_editor.graph.spring_layout import spring_layout
from tools.map_editor.graph.thumbnails import ThumbnailCache
from tools.map_editor.scenes.side_panel import PanelLayout, render_side_panel
from tools.map_editor.scenes.tile_picker import PortalOption, TilePicker


NODE_BG = (28, 28, 36)
NODE_BORDER = (90, 90, 110)
NODE_BORDER_HOVER = (180, 180, 200)
NODE_BORDER_SELECTED = (240, 220, 120)
EDGE_COLOR = (110, 130, 160)
EDGE_COLOR_HOVER = (180, 200, 230)
EDGE_COLOR_SELECTED = (240, 220, 120)
ARROW_LEN = 16
ARROW_HALF_WIDTH = 8
NODE_PADDING = 8
LABEL_HEIGHT = 18
CLICK_PIXEL_THRESHOLD = 4
EDGE_PICK_THRESHOLD_PX = 8

PANEL_WIDTH_DEFAULT = 360
PANEL_WIDTH_MIN = 240
PANEL_WIDTH_MAX_RESERVE = 200  # leave at least this much for the graph
TOAST_MS = 1400


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

        self._panel_width = PANEL_WIDTH_DEFAULT
        self._resizing_panel = False
        self._handle_hovered = False
        self._panel_layout: PanelLayout | None = None
        self._hovered_copy_idx: int | None = None
        self._panel_scroll_y = 0
        self._last_selection_id: int | None = None

        self._toast_text: str | None = None
        self._toast_until_ms = 0

        self._editor = EditorState()
        self._tile_picker: TilePicker | None = None

    # ── input ────────────────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if self._tile_picker is not None:
                self._tile_picker.handle_event(event)
                continue
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
        if event.button == 1 and self._on_handle(event.pos):
            self._resizing_panel = True
            return
        if self._in_panel(event.pos):
            if event.button == 1:
                self._maybe_copy(event.pos)
            return
        if event.button == 1 and self._editor.enabled and self._editor.step in (
            STEP_SOURCE_NODE, STEP_DEST_NODE
        ):
            hit_node = self._node_at_screen(event.pos)
            if hit_node is not None:
                self._on_editor_node_click(hit_node)
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
        if event.button == 1:
            self._resizing_panel = False
            if self._drag_node_id is not None:
                if self._drag_total_pixels <= CLICK_PIXEL_THRESHOLD:
                    self._selection = self._graph.nodes_by_id[self._drag_node_id]
                self._drag_node_id = None
        if event.button in (1, 2, 3):
            self._panning = False
            self._last_mouse = None

    def _on_mouse_motion(self, event: pygame.event.Event) -> None:
        if self._resizing_panel:
            screen_w = pygame.display.get_surface().get_width()
            new_width = screen_w - event.pos[0]
            self._panel_width = max(
                PANEL_WIDTH_MIN, min(screen_w - PANEL_WIDTH_MAX_RESERVE, new_width)
            )
            return

        self._handle_hovered = self._on_handle(event.pos)
        if self._in_panel(event.pos):
            self._hover_node = None
            self._hover_edge_idx = None
            self._hovered_copy_idx = self._copy_target_at(event.pos)
        else:
            self._hovered_copy_idx = None
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
        if self._mouse_in_panel():
            self._scroll_panel(-event.y * 60)
            return
        factor = 1.15 if event.y > 0 else 1.0 / 1.15
        self._zoom = max(0.25, min(2.5, self._zoom * factor))

    def _mouse_in_panel(self) -> bool:
        return self._in_panel(pygame.mouse.get_pos())

    def _scroll_panel(self, delta: int) -> None:
        if self._panel_layout is None:
            return
        max_scroll = max(
            0, self._panel_layout.content_height - self._panel_layout.viewable_height
        )
        self._panel_scroll_y = max(0, min(max_scroll, self._panel_scroll_y + delta))

    def _on_key_down(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_e and not (event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
            self._toggle_edit_mode()
            return
        if event.key == pygame.K_s and not (event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
            if self._editor.enabled:
                self._save_pending_edits()
                return
        if event.key in (pygame.K_0, pygame.K_KP_0):
            self._needs_fit = True
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if isinstance(self._selection, GraphNode):
                self._on_open_map(self._selection)
        elif event.key == pygame.K_ESCAPE:
            if self._editor.enabled:
                if self._editor.step != STEP_SOURCE_NODE:
                    self._editor.cancel_cycle("Cancelled")
                else:
                    self._editor.disable()
                return
            self._selection = None

    # ── editor flow ──────────────────────────────────────────────────────

    def _toggle_edit_mode(self) -> None:
        if self._editor.enabled:
            self._editor.disable()
        else:
            self._editor.enable()

    def _on_editor_node_click(self, map_id: str) -> None:
        if self._editor.step == STEP_SOURCE_NODE:
            portals = self._portals_for_map(map_id)
            self._editor.set_source_map(map_id)
            self._open_picker_for_source(map_id, portals)
        elif self._editor.step == STEP_DEST_NODE:
            self._editor.set_dest_map(map_id)
            self._open_picker_for_dest(map_id)

    def _portals_for_map(self, map_id: str) -> list[PortalOption]:
        opts: list[PortalOption] = []
        for edge in self._graph.edges:
            if edge.source != map_id:
                continue
            opts.append(
                PortalOption(
                    portal_obj_id=edge.portal_obj_id,
                    source_tile=edge.source_tile,
                    target_map=edge.target,
                    target_tile=edge.target_tile,
                )
            )
        return opts

    def _open_picker_for_source(
        self, map_id: str, portals: list[PortalOption]
    ) -> None:
        node = self._graph.nodes_by_id[map_id]
        hint = (
            f"Click an existing portal to retarget on {map_id}, or any tile to add new"
            if portals
            else f"{map_id} has no portals — click any tile to add one"
        )
        self._tile_picker = TilePicker(
            node=node,
            thumbnails=self._thumbnails,
            font=self._font,
            small_font=self._small_font,
            hint_text=hint,
            mode="portals",
            on_pick=self._on_source_tile_picked,
            portals=portals,
        )

    def _open_picker_for_dest(self, map_id: str) -> None:
        node = self._graph.nodes_by_id[map_id]
        self._tile_picker = TilePicker(
            node=node,
            thumbnails=self._thumbnails,
            font=self._font,
            small_font=self._small_font,
            hint_text=f"Click arrival tile on {map_id}",
            mode="free",
            on_pick=self._on_dest_tile_picked,
        )

    def _on_source_tile_picked(self, picked) -> None:
        self._tile_picker = None
        if picked is None:
            self._editor.cancel_cycle("Cancelled")
            return
        if isinstance(picked, PortalOption):
            self._editor.set_source_portal(
                portal_obj_id=picked.portal_obj_id,
                source_tile=picked.source_tile,
                original_target_map=picked.target_map,
                original_target_tile=picked.target_tile,
            )
        else:
            # `picked` is a (col, row) tile — user wants a new portal here.
            self._editor.set_new_source_tile(picked)

    def _on_dest_tile_picked(self, picked) -> None:
        self._tile_picker = None
        if picked is None:
            self._editor.cancel_cycle("Cancelled")
            return
        assert self._editor.source_map is not None
        source_node = self._graph.nodes_by_id[self._editor.source_map]
        edit = self._editor.record_edit(
            source_tmx=source_node.tmx_path, dest_tile=picked
        )
        self._apply_edit_to_graph(edit)

    def _apply_edit_to_graph(self, edit) -> None:
        """Update the in-memory graph so the visualization reflects the pending edit."""
        if edit.is_new:
            self._graph.edges.append(
                GraphEdge(
                    source=edit.source_map_id,
                    target=edit.new_target_map,
                    source_tile=edit.source_tile,
                    target_tile=edit.new_target_tile,
                    portal_obj_id=edit.portal_obj_id,
                )
            )
            return
        for e in self._graph.edges:
            if e.source == edit.source_map_id and e.portal_obj_id == edit.portal_obj_id:
                e.target = edit.new_target_map
                e.target_tile = edit.new_target_tile

    def _save_pending_edits(self) -> None:
        if not self._editor.pending:
            self._editor.last_message = "No pending edits to save."
            return
        n = 0
        for (map_id, obj_id), edit in list(self._editor.pending.items()):
            try:
                if edit.is_new:
                    real_id = create_portal(
                        tmx_path=edit.source_tmx,
                        source_tile=edit.source_tile,
                        new_target_map=edit.new_target_map,
                        new_target_tile=edit.new_target_tile,
                    )
                    self._replace_temp_portal_id(map_id, edit.portal_obj_id, real_id)
                else:
                    save_portal_target(
                        tmx_path=edit.source_tmx,
                        portal_obj_id=edit.portal_obj_id,
                        new_target_map=edit.new_target_map,
                        new_target_tile=edit.new_target_tile,
                    )
                n += 1
            except Exception as exc:
                self._editor.last_message = f"Save failed for {map_id}: {exc}"
                return
        self._editor.pending.clear()
        self._editor.last_message = f"Saved {n} portal edit(s) to TMX (.bak created)."
        self._toast_text = self._editor.last_message
        self._toast_until_ms = pygame.time.get_ticks() + TOAST_MS

    def _replace_temp_portal_id(self, map_id: str, temp_id: int, real_id: int) -> None:
        for e in self._graph.edges:
            if e.source == map_id and e.portal_obj_id == temp_id:
                e.portal_obj_id = real_id
                return

    # ── copy handling ────────────────────────────────────────────────────

    def _copy_target_at(self, pos: tuple[int, int]) -> int | None:
        if self._panel_layout is None:
            return None
        for i, (rect, _) in enumerate(self._panel_layout.copy_targets):
            if rect.collidepoint(pos):
                return i
        return None

    def _maybe_copy(self, pos: tuple[int, int]) -> None:
        idx = self._copy_target_at(pos)
        if idx is None or self._panel_layout is None:
            return
        _, text = self._panel_layout.copy_targets[idx]
        self._copy_to_clipboard(text)
        self._toast_text = f"Copied: {text}"
        self._toast_until_ms = pygame.time.get_ticks() + TOAST_MS

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
        except (pygame.error, AttributeError):
            pass

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

        # Reset scroll when the selection changes.
        sel_id = id(self._selection) if self._selection is not None else None
        if sel_id != self._last_selection_id:
            self._panel_scroll_y = 0
            self._last_selection_id = sel_id

        self._panel_layout = render_side_panel(
            screen=screen,
            selection=self._selection,
            graph=self._graph,
            thumbnails=self._thumbnails,
            font=self._font,
            small_font=self._small_font,
            header_font=self._header_font,
            panel_width=self._panel_width,
            handle_hovered=self._handle_hovered or self._resizing_panel,
            hovered_copy_idx=self._hovered_copy_idx,
            scroll_y=self._panel_scroll_y,
            now_ms=pygame.time.get_ticks(),
        )
        # Clamp in case panel/content size shrank after a resize.
        max_scroll = max(
            0, self._panel_layout.content_height - self._panel_layout.viewable_height
        )
        if self._panel_scroll_y > max_scroll:
            self._panel_scroll_y = max_scroll
        self._render_toast(screen)

        if self._editor.enabled:
            self._render_editor_hud(screen)
        if self._tile_picker is not None:
            self._tile_picker.render(screen, pygame.time.get_ticks())

    def _render_edges(self, screen: pygame.Surface) -> None:
        # Two passes: regular edges first, then hover/selected on top so the
        # label and arrow aren't covered by other lines.
        decorated: list[tuple[int, GraphEdge, tuple[int, int], tuple[int, int], bool, bool]] = []
        for idx, edge in enumerate(self._graph.edges):
            endpoints = self._edge_endpoints(edge)
            if endpoints is None:
                continue
            (sx, sy), (tx, ty) = endpoints
            is_selected = self._selection is edge
            is_hover = self._hover_edge_idx == idx
            decorated.append((idx, edge, (sx, sy), (tx, ty), is_selected, is_hover))

        for _, _, (sx, sy), (tx, ty), is_selected, is_hover in decorated:
            if is_selected or is_hover:
                continue
            self._draw_arrow(screen, sx, sy, tx, ty, EDGE_COLOR, 1)

        for _, edge, (sx, sy), (tx, ty), is_selected, is_hover in decorated:
            if not (is_selected or is_hover):
                continue
            if is_selected:
                color, width = EDGE_COLOR_SELECTED, 3
            else:
                color, width = EDGE_COLOR_HOVER, 2
            self._draw_arrow(screen, sx, sy, tx, ty, color, width)
            dest = self._graph.nodes_by_id.get(edge.target)
            if dest is not None:
                self._draw_edge_label(screen, sx, sy, tx, ty, dest.display_name)

    def _draw_arrow(
        self,
        screen: pygame.Surface,
        sx: int,
        sy: int,
        tx: int,
        ty: int,
        color: tuple[int, int, int],
        width: int,
    ) -> None:
        dx, dy = tx - sx, ty - sy
        length = math.hypot(dx, dy)
        if length < 1.0:
            return
        angle = math.atan2(dy, dx)
        # Line stops at the arrow base so the arrowhead's apex coincides with (tx, ty).
        base_x = tx - math.cos(angle) * ARROW_LEN
        base_y = ty - math.sin(angle) * ARROW_LEN
        pygame.draw.line(screen, color, (sx, sy), (base_x, base_y), width)
        left = (
            base_x + math.cos(angle + math.pi / 2) * ARROW_HALF_WIDTH,
            base_y + math.sin(angle + math.pi / 2) * ARROW_HALF_WIDTH,
        )
        right = (
            base_x + math.cos(angle - math.pi / 2) * ARROW_HALF_WIDTH,
            base_y + math.sin(angle - math.pi / 2) * ARROW_HALF_WIDTH,
        )
        pygame.draw.polygon(screen, color, [(tx, ty), left, right])

    def _draw_edge_label(
        self,
        screen: pygame.Surface,
        sx: int,
        sy: int,
        tx: int,
        ty: int,
        text: str,
    ) -> None:
        # Place label two-thirds along the edge so it sits closer to the destination.
        lx = int(sx + (tx - sx) * 0.66)
        ly = int(sy + (ty - sy) * 0.66)
        label = self._small_font.render(text, True, (240, 240, 240))
        pad_x, pad_y = 6, 2
        bg = pygame.Surface(
            (label.get_width() + pad_x * 2, label.get_height() + pad_y * 2),
            pygame.SRCALPHA,
        )
        bg.fill((20, 20, 28, 210))
        bg_rect = bg.get_rect(center=(lx, ly))
        screen.blit(bg, bg_rect.topleft)
        screen.blit(label, (bg_rect.left + pad_x, bg_rect.top + pad_y))

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
            f"[click=select  drag=move  wheel=zoom  Enter=open  0=fit  E=edit]",
            True,
            (220, 220, 220),
        )
        screen.blit(hud, (10, 10))

    def _render_editor_hud(self, screen: pygame.Surface) -> None:
        lines = [
            f"EDIT MODE — {self._editor.step_label()}",
            self._editor.last_message or "",
            f"pending: {len(self._editor.pending)}   [S] save   [Esc] cancel/exit",
        ]
        rendered = [self._font.render(line, True, (255, 245, 200)) for line in lines if line]
        width = max((s.get_width() for s in rendered), default=0) + 24
        height = sum(s.get_height() for s in rendered) + 16
        bg = pygame.Surface((width, height), pygame.SRCALPHA)
        bg.fill((40, 30, 10, 220))
        screen.blit(bg, (10, 40))
        y = 48
        for s in rendered:
            screen.blit(s, (22, y))
            y += s.get_height()

    def _render_toast(self, screen: pygame.Surface) -> None:
        if self._toast_text is None:
            return
        if pygame.time.get_ticks() > self._toast_until_ms:
            self._toast_text = None
            return
        label = self._font.render(self._toast_text, True, (255, 255, 255))
        pad_x, pad_y = 12, 6
        bg = pygame.Surface(
            (label.get_width() + pad_x * 2, label.get_height() + pad_y * 2),
            pygame.SRCALPHA,
        )
        bg.fill((30, 80, 50, 230))
        sw, sh = screen.get_size()
        x = sw - self._panel_width - bg.get_width() - 16
        y = sh - bg.get_height() - 16
        screen.blit(bg, (x, y))
        screen.blit(label, (x + pad_x, y + pad_y))

    def update(self, dt: float) -> None:
        return

    # ── geometry helpers ─────────────────────────────────────────────────

    def _graph_viewport(self, screen_size: tuple[int, int]) -> tuple[int, int, int, int]:
        return (0, 0, max(1, screen_size[0] - self._panel_width), screen_size[1])

    def _in_panel(self, pos: tuple[int, int]) -> bool:
        return self._panel_layout is not None and self._panel_layout.rect.collidepoint(pos)

    def _on_handle(self, pos: tuple[int, int]) -> bool:
        return self._panel_layout is not None and self._panel_layout.handle_rect.collidepoint(pos)

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
        """Return the visible line endpoints (clipped to each node's outer border).

        The interior points are the portal tile positions on each thumbnail;
        we then clip them to the node bounding rects so the arrowhead apex
        sits on the destination node's outer edge instead of being covered
        by the thumbnail.
        """
        src_view = self._node_views.get(edge.source)
        dst_view = self._node_views.get(edge.target)
        if src_view is None or dst_view is None:
            return None
        src_inner = self._portal_point_on_node(src_view, edge.source_tile)
        dst_inner = self._portal_point_on_node(dst_view, edge.target_tile)
        src_rect = self._node_rect(src_view)
        dst_rect = self._node_rect(dst_view)
        src_pt = _exit_point(src_inner, dst_inner, src_rect) or src_inner
        dst_pt = _exit_point(dst_inner, src_inner, dst_rect) or dst_inner
        return src_pt, dst_pt

    def _node_rect(self, view: _NodeView) -> pygame.Rect:
        cx, cy = self._layout_to_screen(view.layout_x, view.layout_y)
        w = int(view.width * self._zoom)
        h = int(view.height * self._zoom)
        return pygame.Rect(cx - w // 2, cy - h // 2, w, h)

    def _portal_point_on_node(
        self, view: _NodeView, tile: tuple[int, int]
    ) -> tuple[int, int]:
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


def _exit_point(
    inside: tuple[int, int], outside: tuple[int, int], rect: pygame.Rect
) -> tuple[int, int] | None:
    """Where the ray from `inside` toward `outside` crosses the rect's border.

    `inside` is expected to lie inside `rect`. Returns None if the segment
    doesn't actually cross the border (e.g., `outside` also inside).
    """
    sx, sy = inside
    tx, ty = outside
    dx, dy = tx - sx, ty - sy
    if dx == 0 and dy == 0:
        return None
    t_exit = 1.0
    if dx > 0:
        t_exit = min(t_exit, (rect.right - sx) / dx)
    elif dx < 0:
        t_exit = min(t_exit, (rect.left - sx) / dx)
    if dy > 0:
        t_exit = min(t_exit, (rect.bottom - sy) / dy)
    elif dy < 0:
        t_exit = min(t_exit, (rect.top - sy) / dy)
    if t_exit <= 0:
        return None
    return (int(sx + t_exit * dx), int(sy + t_exit * dy))


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
