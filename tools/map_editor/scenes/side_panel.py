"""Right-side detail panel for the graph view.

Shows either a node's details (map metadata, NPCs, item boxes, badges)
or a portal edge's details (two stacked thumbnails with outbound/inbound
markers on the source and destination tiles).

The panel:
  - is resizable via a drag handle on its left edge,
  - scrolls vertically (mouse wheel) when content overflows, with a
    visible scrollbar,
  - exposes click-to-copy targets,
  - pulses the portal markers (animation matches maps_graph.html).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Union

import pygame

from tools.map_editor.graph.portal_graph import GraphEdge, GraphNode, PortalGraph
from tools.map_editor.graph.sprite_cache import SpriteCache
from tools.map_editor.graph.thumbnails import ThumbnailCache


PANEL_BG = (22, 22, 30)
PANEL_BORDER = (60, 60, 80)
HANDLE_COLOR = (90, 90, 120)
HANDLE_HOVER = (140, 160, 200)
HANDLE_WIDTH = 6
SCROLLBAR_WIDTH = 8
SCROLLBAR_TRACK = (40, 40, 56)
SCROLLBAR_THUMB = (110, 120, 150)
FOOTER_RESERVE = 30
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
# Pulse periods (ms).
PULSE_PERIOD_MS = 800
BLINK_PERIOD_MS = 450


Selection = Union[GraphNode, GraphEdge, None]


@dataclass
class PanelLayout:
    rect: pygame.Rect
    handle_rect: pygame.Rect
    content_height: int = 0
    viewable_height: int = 0
    copy_targets: list[tuple[pygame.Rect, str]] = field(default_factory=list)


def render_side_panel(
    screen: pygame.Surface,
    selection: Selection,
    graph: PortalGraph,
    thumbnails: ThumbnailCache,
    sprites: SpriteCache,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
    panel_width: int,
    handle_hovered: bool,
    hovered_copy_idx: int | None,
    scroll_y: int,
    now_ms: int,
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

    content_clip = pygame.Rect(
        rect.left,
        rect.top,
        rect.width - SCROLLBAR_WIDTH - 2,
        rect.height - FOOTER_RESERVE,
    )

    layout = PanelLayout(rect=rect, handle_rect=handle_rect, viewable_height=content_clip.height)

    prev_clip = screen.get_clip()
    screen.set_clip(content_clip)
    start_y = rect.top + 14 - scroll_y

    if selection is None:
        msg = font.render("Click a map or portal edge.", True, TEXT_DIM)
        screen.blit(msg, (rect.left + 14, start_y + 2))
        final_y = start_y + msg.get_height()
    elif isinstance(selection, GraphNode):
        final_y = _render_node(
            screen, rect, selection, thumbnails, sprites,
            font, small_font, header_font, layout, start_y,
        )
    else:
        final_y = _render_edge(
            screen, rect, selection, graph, thumbnails, sprites,
            font, small_font, header_font, layout, start_y, now_ms,
        )

    screen.set_clip(prev_clip)

    layout.content_height = (final_y - start_y) + 28  # top + bottom padding

    _render_footer(screen, rect, selection, small_font)
    _render_scrollbar(screen, rect, scroll_y, layout.content_height, layout.viewable_height)
    _filter_copy_targets(layout, content_clip)
    _highlight_hovered_copy(screen, layout, hovered_copy_idx)
    return layout


def _filter_copy_targets(layout: PanelLayout, clip: pygame.Rect) -> None:
    layout.copy_targets = [(r, t) for r, t in layout.copy_targets if clip.colliderect(r)]


def _highlight_hovered_copy(
    screen: pygame.Surface, layout: PanelLayout, hovered_idx: int | None
) -> None:
    if hovered_idx is None or hovered_idx >= len(layout.copy_targets):
        return
    rect, _ = layout.copy_targets[hovered_idx]
    overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    overlay.fill(COPY_HOVER_BG)
    screen.blit(overlay, rect.topleft)


def _render_footer(
    screen: pygame.Surface,
    rect: pygame.Rect,
    selection: Selection,
    small_font: pygame.font.Font,
) -> None:
    if selection is None:
        return
    if isinstance(selection, GraphNode):
        text = "[Enter] open  [Esc] deselect  click value to copy"
    else:
        text = "[Esc] deselect  click value to copy  wheel to scroll"
    label = small_font.render(text, True, TEXT_DIM)
    screen.blit(label, (rect.left + 14, rect.bottom - label.get_height() - 10))


def _render_scrollbar(
    screen: pygame.Surface,
    rect: pygame.Rect,
    scroll_y: int,
    content_height: int,
    viewable_height: int,
) -> None:
    if content_height <= viewable_height:
        return
    track = pygame.Rect(
        rect.right - SCROLLBAR_WIDTH - 2,
        rect.top + 4,
        SCROLLBAR_WIDTH,
        viewable_height - 8,
    )
    pygame.draw.rect(screen, SCROLLBAR_TRACK, track, border_radius=3)

    ratio = viewable_height / content_height
    thumb_h = max(20, int(track.height * ratio))
    max_scroll = content_height - viewable_height
    thumb_y_off = int((track.height - thumb_h) * scroll_y / max_scroll) if max_scroll > 0 else 0
    thumb = pygame.Rect(track.x, track.y + thumb_y_off, track.width, thumb_h)
    pygame.draw.rect(screen, SCROLLBAR_THUMB, thumb, border_radius=3)


def _render_node(
    screen: pygame.Surface,
    rect: pygame.Rect,
    node: GraphNode,
    thumbnails: ThumbnailCache,
    sprites: SpriteCache,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
    layout: PanelLayout,
    y: int,
) -> int:
    x = rect.left + 14
    inner_w = rect.width - 28 - SCROLLBAR_WIDTH

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
        max_h = max(200, rect.height - 240)
        scaled = _fit_image(thumb, inner_w, max_h)
        screen.blit(scaled, (x, y))
        _overlay_actors(
            screen, pygame.Rect(x, y, scaled.get_width(), scaled.get_height()),
            node, sprites,
        )
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
        for npc in node.npcs:
            label = f"{npc.name or npc.npc_id}"
            if npc.position:
                label += f"  @{npc.position[0]},{npc.position[1]}"
            y = _render_dim_line(screen, x, y, label, small_font, layout)

    y += SECTION_GAP
    y = _render_section_title(screen, x, y, f"Item Boxes ({len(node.item_boxes)})", font)
    if not node.item_boxes:
        y = _render_dim_line(screen, x, y, "—", small_font, layout)
    else:
        for box in node.item_boxes:
            label = f"{box.box_id}"
            if box.position:
                label += f"  @{box.position[0]},{box.position[1]}"
            y = _render_dim_line(screen, x, y, label, small_font, layout)

    return y


def _render_edge(
    screen: pygame.Surface,
    rect: pygame.Rect,
    edge: GraphEdge,
    graph: PortalGraph,
    thumbnails: ThumbnailCache,
    sprites: SpriteCache,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
    layout: PanelLayout,
    y: int,
    now_ms: int,
) -> int:
    x = rect.left + 14
    inner_w = rect.width - 28 - SCROLLBAR_WIDTH

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

    # Each map can be as tall as needed to honor the panel width (preserving
    # aspect ratio). Content that runs past the viewable area is reachable
    # via the scrollbar.
    map_max_h = rect.height  # effectively uncapped; width is the binding constraint
    y += SECTION_GAP
    y = _render_section_title(screen, x, y, "Source", small_font)
    if source_node is not None:
        y = _render_map_with_marker(
            screen, x, y, inner_w, map_max_h, source_node, thumbnails, sprites,
            edge.source_tile, kind="outbound", now_ms=now_ms,
        )
    y += SECTION_GAP

    y = _render_section_title(screen, x, y, "Destination", small_font)
    if target_node is not None:
        y = _render_map_with_marker(
            screen, x, y, inner_w, map_max_h, target_node, thumbnails, sprites,
            edge.target_tile, kind="inbound", now_ms=now_ms,
        )

    return y


def _render_map_with_marker(
    screen: pygame.Surface,
    x: int,
    y: int,
    max_w: int,
    max_h: int,
    node: GraphNode,
    thumbnails: ThumbnailCache,
    sprites: SpriteCache,
    tile: tuple[int, int],
    kind: str,
    now_ms: int,
) -> int:
    thumb = thumbnails.get_full(node.tmx_path) or thumbnails.get(node.tmx_path)
    if thumb is None:
        return y
    scaled = _fit_image(thumb, max_w, max_h)
    screen.blit(scaled, (x, y))
    map_rect = pygame.Rect(x, y, scaled.get_width(), scaled.get_height())
    _overlay_actors(screen, map_rect, node, sprites)

    map_w_px, map_h_px = node.map_size_px
    tile_w_px, tile_h_px = node.tile_size_px
    if map_w_px > 0 and map_h_px > 0:
        sw, sh = scaled.get_size()
        col, row = tile
        mw = max(4, int(tile_w_px * sw / map_w_px))
        mh = max(4, int(tile_h_px * sh / map_h_px))
        mx = x + int(col * tile_w_px * sw / map_w_px)
        my = y + int(row * tile_h_px * sh / map_h_px)
        _draw_marker(screen, pygame.Rect(mx, my, mw, mh), kind, now_ms)

    return y + scaled.get_height() + 2


def _overlay_actors(
    screen: pygame.Surface,
    map_rect: pygame.Rect,
    node: GraphNode,
    sprites: SpriteCache,
) -> None:
    """Blit NPC and item-box sprites at their tile positions on a rendered map."""
    map_w_px, map_h_px = node.map_size_px
    tile_w_px, tile_h_px = node.tile_size_px
    if map_w_px <= 0 or map_h_px <= 0 or tile_w_px <= 0 or tile_h_px <= 0:
        return
    sx = map_rect.width / map_w_px
    sy = map_rect.height / map_h_px
    tw_screen = max(6, int(tile_w_px * sx))
    th_screen = max(6, int(tile_h_px * sy))

    def _blit(icon, col: int, row: int) -> None:
        if icon is None:
            return
        scaled = pygame.transform.smoothscale(icon, (tw_screen, th_screen))
        bx = map_rect.left + int(col * tile_w_px * sx)
        by = map_rect.top + int(row * tile_h_px * sy)
        screen.blit(scaled, (bx, by))

    for npc in node.npcs:
        if npc.position is None:
            continue
        _blit(sprites.npc_icon(npc.sprite), npc.position[0], npc.position[1])

    for box in node.item_boxes:
        if box.position is None:
            continue
        _blit(sprites.item_box_icon(box.sprite), box.position[0], box.position[1])


def _draw_marker(
    screen: pygame.Surface, rect: pygame.Rect, kind: str, now_ms: int
) -> None:
    # Pulse phase in [0, 1) — used to grow/fade an outer ring like the CSS animation.
    pulse_phase = (now_ms % PULSE_PERIOD_MS) / PULSE_PERIOD_MS
    pulse_radius_factor = pulse_phase
    pulse_alpha = int(220 * (1.0 - pulse_phase))
    # Blink phase: dot visible for the first half of each blink period.
    blink_on = (now_ms % BLINK_PERIOD_MS) < (BLINK_PERIOD_MS / 2)

    cx, cy = rect.center
    if kind == "outbound":
        outer = rect.inflate(6, 6)
        pygame.draw.rect(screen, OUTBOUND_FILL, outer, width=3)
        pygame.draw.rect(screen, OUTBOUND_RING, rect, width=2)
        # Pulsing yellow square ring around the marker.
        max_grow = max(rect.w, rect.h) + 18
        grow = int(max_grow * pulse_radius_factor)
        ring_rect = rect.inflate(grow, grow)
        _draw_alpha_rect(screen, ring_rect, OUTBOUND_RING, pulse_alpha, width=2)
        if blink_on:
            pygame.draw.circle(screen, OUTBOUND_RING, (cx, cy), max(2, min(rect.w, rect.h) // 4))
    else:
        r = max(rect.w, rect.h) // 2 + 3
        pygame.draw.circle(screen, INBOUND_FILL, (cx, cy), r, width=3)
        pygame.draw.circle(screen, INBOUND_RING, (cx, cy), r + 4, width=1)
        # Pulsing cyan ring expanding outward.
        pulse_r = r + int(28 * pulse_radius_factor)
        _draw_alpha_circle(screen, (cx, cy), pulse_r, INBOUND_RING, pulse_alpha, width=2)
        if blink_on:
            pygame.draw.circle(screen, INBOUND_FILL, (cx, cy), max(2, r // 3))


def _draw_alpha_rect(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    alpha: int,
    width: int,
) -> None:
    if alpha <= 0 or rect.w <= 0 or rect.h <= 0:
        return
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), width=width)
    screen.blit(surf, rect.topleft)


def _draw_alpha_circle(
    screen: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    alpha: int,
    width: int,
) -> None:
    if alpha <= 0 or radius <= 0:
        return
    size = (radius + width) * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*color, alpha), (size // 2, size // 2), radius, width=width)
    screen.blit(surf, (center[0] - size // 2, center[1] - size // 2))


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
    sw, sh = surf.get_size()
    if sw == 0 or sh == 0:
        return surf
    scale = min(max_w / sw, max_h / sh)
    new_w = max(1, int(sw * scale))
    new_h = max(1, int(sh * scale))
    if (new_w, new_h) == (sw, sh):
        return surf
    if scale > 1.0:
        return pygame.transform.scale(surf, (new_w, new_h))
    return pygame.transform.smoothscale(surf, (new_w, new_h))
