"""Right-side detail panel for the graph view.

Shows either a node's details (map metadata, NPCs, item boxes, badges)
or a portal edge's details (two thumbnails with outbound/inbound markers
on the source and destination tiles).

The panel is resizable: callers pass in the current width, and the
returned PanelLayout exposes the resize-handle rect plus a list of
click-to-copy targets (so the graph scene can dispatch clicks).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

import pygame

from tools.map_editor.graph.portal_graph import GraphEdge, GraphNode, PortalGraph
from tools.map_editor.graph.thumbnails import ThumbnailCache


PANEL_BG = (22, 22, 30)
PANEL_BORDER = (60, 60, 80)
HANDLE_COLOR = (90, 90, 120)
HANDLE_HOVER = (140, 160, 200)
HANDLE_WIDTH = 6
TEXT = (220, 220, 220)
TEXT_DIM = (160, 160, 170)
TEXT_HEADER = (250, 230, 130)
SECTION_TITLE = (130, 200, 240)
COPY_HOVER_BG = (60, 90, 140, 90)
BADGE_BG = (50, 80, 110)
BADGE_FG = (220, 240, 255)
BADGE_PAD_X = 6
BADGE_PAD_Y = 2
SECTION_GAP = 8

# Marker colors matching maps_graph.html.
OUTBOUND_FILL = (255, 74, 42)
OUTBOUND_RING = (255, 210, 0)
INBOUND_FILL = (58, 207, 255)
INBOUND_RING = (184, 243, 255)


Selection = Union[GraphNode, GraphEdge, None]


@dataclass
class PanelLayout:
    rect: pygame.Rect
    handle_rect: pygame.Rect
    copy_targets: list[tuple[pygame.Rect, str]] = field(default_factory=list)


def render_side_panel(
    screen: pygame.Surface,
    selection: Selection,
    graph: PortalGraph,
    thumbnails: ThumbnailCache,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
    panel_width: int,
    handle_hovered: bool,
    hovered_copy_idx: int | None,
) -> PanelLayout:
    sw, sh = screen.get_size()
    rect = pygame.Rect(sw - panel_width, 0, panel_width, sh)
    pygame.draw.rect(screen, PANEL_BG, rect)

    handle_rect = pygame.Rect(rect.left - HANDLE_WIDTH // 2, 0, HANDLE_WIDTH, sh)
    pygame.draw.line(
        screen,
        HANDLE_HOVER if handle_hovered else HANDLE_COLOR,
        (rect.left, 0),
        (rect.left, sh),
        2 if handle_hovered else 1,
    )

    layout = PanelLayout(rect=rect, handle_rect=handle_rect)

    if selection is None:
        _render_empty(screen, rect, font)
    elif isinstance(selection, GraphNode):
        _render_node(screen, rect, selection, thumbnails, font, small_font, header_font, layout)
    else:
        _render_edge(
            screen, rect, selection, graph, thumbnails,
            font, small_font, header_font, layout,
        )

    _highlight_hovered_copy(screen, layout, hovered_copy_idx)
    return layout


def _highlight_hovered_copy(
    screen: pygame.Surface, layout: PanelLayout, hovered_idx: int | None
) -> None:
    if hovered_idx is None or hovered_idx >= len(layout.copy_targets):
        return
    rect, _ = layout.copy_targets[hovered_idx]
    overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    overlay.fill(COPY_HOVER_BG)
    screen.blit(overlay, rect.topleft)


def _render_empty(screen: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font) -> None:
    msg = font.render("Click a map or portal edge.", True, TEXT_DIM)
    screen.blit(msg, (rect.left + 14, rect.top + 16))


def _render_node(
    screen: pygame.Surface,
    rect: pygame.Rect,
    node: GraphNode,
    thumbnails: ThumbnailCache,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
    layout: PanelLayout,
) -> None:
    x = rect.left + 14
    y = rect.top + 14
    inner_w = rect.width - 28

    title_surf = header_font.render(node.display_name, True, TEXT_HEADER)
    title_rect = pygame.Rect(x, y, title_surf.get_width(), title_surf.get_height())
    screen.blit(title_surf, title_rect.topleft)
    layout.copy_targets.append((title_rect, node.display_name))
    y += title_surf.get_height() + 2

    sub_surf = small_font.render(node.map_id, True, TEXT_DIM)
    sub_rect = pygame.Rect(x, y, sub_surf.get_width(), sub_surf.get_height())
    screen.blit(sub_surf, sub_rect.topleft)
    layout.copy_targets.append((sub_rect, node.map_id))
    y += sub_surf.get_height() + 6

    thumb = thumbnails.get_full(node.tmx_path) or thumbnails.get(node.tmx_path)
    if thumb is not None:
        # Reserve ~240px for header, badges, footer, and a few list rows; the
        # rest is the map. Widening the panel grows the map until the cap.
        max_h = max(200, rect.height - 240)
        scaled = _fit_image(thumb, inner_w, max_h)
        screen.blit(scaled, (x, y))
        y += scaled.get_height() + SECTION_GAP

    badges = _build_badges(node)
    if badges:
        y = _render_badges(screen, x, y, inner_w, badges, small_font)
        y += SECTION_GAP

    if node.bgm:
        y = _render_kv(screen, x, y, "bgm", node.bgm, font, small_font, layout)

    if node.encounter:
        summary = _summarize_encounter(node.encounter)
        if summary:
            y = _render_kv(screen, x, y, "encounter", summary, font, small_font, layout)

    y += SECTION_GAP
    y = _render_section_title(screen, x, y, f"NPCs ({len(node.npcs)})", font)
    if not node.npcs:
        y = _render_dim_line(screen, x, y, "—", small_font, layout)
    else:
        for npc in node.npcs[:12]:
            label = f"{npc.name or npc.npc_id}"
            if npc.position:
                label += f"  @{npc.position[0]},{npc.position[1]}"
            y = _render_dim_line(screen, x, y, label, small_font, layout)
        if len(node.npcs) > 12:
            y = _render_dim_line(
                screen, x, y, f"  …+{len(node.npcs) - 12} more", small_font, layout
            )

    y += SECTION_GAP
    y = _render_section_title(screen, x, y, f"Item Boxes ({len(node.item_boxes)})", font)
    if not node.item_boxes:
        y = _render_dim_line(screen, x, y, "—", small_font, layout)
    else:
        for box in node.item_boxes[:12]:
            label = f"{box.box_id}"
            if box.position:
                label += f"  @{box.position[0]},{box.position[1]}"
            y = _render_dim_line(screen, x, y, label, small_font, layout)

    footer = small_font.render(
        "[Enter] open  [Esc] deselect  click value to copy", True, TEXT_DIM
    )
    screen.blit(footer, (x, rect.bottom - footer.get_height() - 10))


def _render_edge(
    screen: pygame.Surface,
    rect: pygame.Rect,
    edge: GraphEdge,
    graph: PortalGraph,
    thumbnails: ThumbnailCache,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
    layout: PanelLayout,
) -> None:
    x = rect.left + 14
    y = rect.top + 14
    inner_w = rect.width - 28

    source_node = graph.nodes_by_id.get(edge.source)
    target_node = graph.nodes_by_id.get(edge.target)
    src_name = source_node.display_name if source_node else edge.source
    dst_name = target_node.display_name if target_node else edge.target

    title = header_font.render("Portal", True, TEXT_HEADER)
    screen.blit(title, (x, y))
    y += title.get_height() + 6

    y = _render_kv(
        screen, x, y, "from",
        f"{src_name}  @{edge.source_tile[0]},{edge.source_tile[1]}",
        font, small_font, layout,
    )
    y = _render_kv(
        screen, x, y, "to",
        f"{dst_name}  @{edge.target_tile[0]},{edge.target_tile[1]}",
        font, small_font, layout,
    )

    y += SECTION_GAP
    # Reserve ~60px for the footer; the rest splits evenly between the two maps.
    remaining = rect.bottom - y - 60
    per_map_max_h = max(200, remaining // 2 - 16)

    y = _render_section_title(screen, x, y, "Source", small_font)
    if source_node is not None:
        y = _render_map_with_marker(
            screen, x, y, inner_w, per_map_max_h, source_node, thumbnails,
            edge.source_tile, kind="outbound",
        )
    y += SECTION_GAP

    y = _render_section_title(screen, x, y, "Destination", small_font)
    if target_node is not None:
        y = _render_map_with_marker(
            screen, x, y, inner_w, per_map_max_h, target_node, thumbnails,
            edge.target_tile, kind="inbound",
        )

    footer = small_font.render("[Esc] deselect  click value to copy", True, TEXT_DIM)
    screen.blit(footer, (x, rect.bottom - footer.get_height() - 10))


def _render_map_with_marker(
    screen: pygame.Surface,
    x: int,
    y: int,
    max_w: int,
    max_h: int,
    node: GraphNode,
    thumbnails: ThumbnailCache,
    tile: tuple[int, int],
    kind: str,
) -> int:
    thumb = thumbnails.get_full(node.tmx_path) or thumbnails.get(node.tmx_path)
    if thumb is None:
        return y
    scaled = _fit_image(thumb, max_w, max_h)
    screen.blit(scaled, (x, y))

    map_w_px, map_h_px = node.map_size_px
    tile_w_px, tile_h_px = node.tile_size_px
    if map_w_px > 0 and map_h_px > 0:
        sw, sh = scaled.get_size()
        col, row = tile
        mw = max(4, int(tile_w_px * sw / map_w_px))
        mh = max(4, int(tile_h_px * sh / map_h_px))
        mx = x + int(col * tile_w_px * sw / map_w_px)
        my = y + int(row * tile_h_px * sh / map_h_px)
        _draw_marker(screen, pygame.Rect(mx, my, mw, mh), kind)

    return y + scaled.get_height() + 2


def _draw_marker(screen: pygame.Surface, rect: pygame.Rect, kind: str) -> None:
    if kind == "outbound":
        outer = rect.inflate(6, 6)
        pygame.draw.rect(screen, OUTBOUND_FILL, outer, width=3)
        pygame.draw.rect(screen, OUTBOUND_RING, rect, width=2)
        cx, cy = rect.center
        pygame.draw.circle(screen, OUTBOUND_RING, (cx, cy), max(2, min(rect.w, rect.h) // 4))
    else:
        cx, cy = rect.center
        r = max(rect.w, rect.h) // 2 + 3
        pygame.draw.circle(screen, INBOUND_FILL, (cx, cy), r, width=3)
        pygame.draw.circle(screen, INBOUND_RING, (cx, cy), r + 4, width=1)
        pygame.draw.circle(screen, INBOUND_FILL, (cx, cy), max(2, r // 3))


def _render_section_title(
    screen: pygame.Surface, x: int, y: int, text: str, font: pygame.font.Font
) -> int:
    label = font.render(text, True, SECTION_TITLE)
    screen.blit(label, (x, y))
    return y + label.get_height() + 2


def _render_kv(
    screen: pygame.Surface,
    x: int,
    y: int,
    key: str,
    value: str,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    layout: PanelLayout,
) -> int:
    key_label = small_font.render(key, True, TEXT_DIM)
    screen.blit(key_label, (x, y))
    val_surf = font.render(value, True, TEXT)
    val_rect = pygame.Rect(x + 80, y - 2, val_surf.get_width(), val_surf.get_height())
    screen.blit(val_surf, val_rect.topleft)
    layout.copy_targets.append((val_rect, value))
    return y + max(key_label.get_height(), val_surf.get_height()) + 2


def _render_dim_line(
    screen: pygame.Surface,
    x: int,
    y: int,
    text: str,
    font: pygame.font.Font,
    layout: PanelLayout,
) -> int:
    label = font.render(text, True, TEXT)
    rect = pygame.Rect(x + 8, y, label.get_width(), label.get_height())
    screen.blit(label, rect.topleft)
    if text not in ("—",):
        layout.copy_targets.append((rect, text))
    return y + label.get_height() + 2


def _build_badges(node: GraphNode) -> list[str]:
    badges: list[str] = []
    if node.has_inn:
        badges.append("Inn")
    if node.has_shop:
        badges.append("Shop")
    if node.has_apothecary:
        badges.append("Apothecary")
    if node.has_magic_core_shop:
        badges.append("Magic Cores")
    return badges


def _render_badges(
    screen: pygame.Surface,
    x: int,
    y: int,
    width: int,
    badges: list[str],
    font: pygame.font.Font,
) -> int:
    cur_x = x
    cur_y = y
    line_h = font.get_linesize() + BADGE_PAD_Y * 2 + 2
    for badge in badges:
        text = font.render(badge, True, BADGE_FG)
        bw = text.get_width() + BADGE_PAD_X * 2
        bh = text.get_height() + BADGE_PAD_Y * 2
        if cur_x + bw > x + width:
            cur_x = x
            cur_y += line_h
        pygame.draw.rect(screen, BADGE_BG, (cur_x, cur_y, bw, bh), border_radius=4)
        screen.blit(text, (cur_x + BADGE_PAD_X, cur_y + BADGE_PAD_Y))
        cur_x += bw + 6
    return cur_y + line_h


def _summarize_encounter(encounter: dict) -> str:
    parts: list[str] = []
    table = encounter.get("table") or encounter.get("group")
    if isinstance(table, str):
        parts.append(table)
    rate = encounter.get("rate") or encounter.get("step_rate")
    if rate is not None:
        parts.append(f"rate={rate}")
    enemies = encounter.get("enemies")
    if isinstance(enemies, list) and enemies:
        parts.append(f"{len(enemies)} entries")
    return ", ".join(parts)


def _fit_image(surf: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    """Scale `surf` to fit (max_w, max_h) while preserving aspect ratio.

    Scales up as well as down, so the displayed map grows with the side
    panel even past the source's native resolution.
    """
    sw, sh = surf.get_size()
    if sw == 0 or sh == 0:
        return surf
    scale = min(max_w / sw, max_h / sh)
    new_w = max(1, int(sw * scale))
    new_h = max(1, int(sh * scale))
    if (new_w, new_h) == (sw, sh):
        return surf
    # smoothscale on upscale can blur pixel art; use plain scale for crispness.
    if scale > 1.0:
        return pygame.transform.scale(surf, (new_w, new_h))
    return pygame.transform.smoothscale(surf, (new_w, new_h))
