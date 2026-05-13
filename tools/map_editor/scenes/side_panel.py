"""Right-side detail panel for the graph view.

Renders either a node's details (map metadata, NPCs, item boxes, badges)
or an edge's details (list of portals between the two maps).
"""

from __future__ import annotations

from typing import Union

import pygame

from tools.map_editor.graph.portal_graph import GraphEdge, GraphNode, PortalGraph


PANEL_WIDTH = 340
PANEL_BG = (22, 22, 30)
PANEL_BORDER = (60, 60, 80)
TEXT = (220, 220, 220)
TEXT_DIM = (160, 160, 170)
TEXT_HEADER = (250, 230, 130)
SECTION_TITLE = (130, 200, 240)
BADGE_BG = (50, 80, 110)
BADGE_FG = (220, 240, 255)
BADGE_PAD_X = 6
BADGE_PAD_Y = 2
SECTION_GAP = 8


Selection = Union[GraphNode, GraphEdge, None]


def render_side_panel(
    screen: pygame.Surface,
    selection: Selection,
    graph: PortalGraph,
    thumbnail: pygame.Surface | None,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
) -> pygame.Rect:
    """Draw the panel anchored to the right edge. Returns its Rect."""
    sw, sh = screen.get_size()
    rect = pygame.Rect(sw - PANEL_WIDTH, 0, PANEL_WIDTH, sh)
    pygame.draw.rect(screen, PANEL_BG, rect)
    pygame.draw.line(screen, PANEL_BORDER, (rect.left, 0), (rect.left, sh), 1)

    if selection is None:
        _render_empty(screen, rect, font)
    elif isinstance(selection, GraphNode):
        _render_node(screen, rect, selection, thumbnail, font, small_font, header_font)
    else:
        _render_edge(screen, rect, selection, graph, font, small_font, header_font)

    return rect


def _render_empty(screen: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font) -> None:
    msg = font.render("Click a map or portal edge.", True, TEXT_DIM)
    screen.blit(msg, (rect.left + 14, rect.top + 16))


def _render_node(
    screen: pygame.Surface,
    rect: pygame.Rect,
    node: GraphNode,
    thumbnail: pygame.Surface | None,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
) -> None:
    x = rect.left + 14
    y = rect.top + 14
    inner_w = rect.width - 28

    title = header_font.render(node.display_name, True, TEXT_HEADER)
    screen.blit(title, (x, y))
    y += title.get_height() + 2

    sub = small_font.render(node.map_id, True, TEXT_DIM)
    screen.blit(sub, (x, y))
    y += sub.get_height() + 4

    if node.yaml_path is not None:
        yaml_label = small_font.render(_truncate(str(node.yaml_path.name), 44), True, TEXT_DIM)
        screen.blit(yaml_label, (x, y))
        y += yaml_label.get_height() + 6

    if thumbnail is not None:
        scaled = _fit_image(thumbnail, inner_w, 200)
        screen.blit(scaled, (x, y))
        y += scaled.get_height() + SECTION_GAP

    badges = _build_badges(node)
    if badges:
        y = _render_badges(screen, x, y, inner_w, badges, small_font)
        y += SECTION_GAP

    if node.bgm:
        y = _render_kv(screen, x, y, "bgm", node.bgm, font, small_font)

    if node.encounter:
        encounter_summary = _summarize_encounter(node.encounter)
        if encounter_summary:
            y = _render_kv(screen, x, y, "encounter", encounter_summary, font, small_font)

    y += SECTION_GAP
    y = _render_section_title(screen, x, y, f"NPCs ({len(node.npcs)})", font)
    if not node.npcs:
        y = _render_dim_line(screen, x, y, "—", small_font)
    else:
        for npc in node.npcs[:12]:
            label = f"{npc.name or npc.npc_id}"
            if npc.position:
                label += f"  @{npc.position[0]},{npc.position[1]}"
            y = _render_dim_line(screen, x, y, label, small_font)
        if len(node.npcs) > 12:
            y = _render_dim_line(screen, x, y, f"  …+{len(node.npcs) - 12} more", small_font)

    y += SECTION_GAP
    y = _render_section_title(screen, x, y, f"Item Boxes ({len(node.item_boxes)})", font)
    if not node.item_boxes:
        y = _render_dim_line(screen, x, y, "—", small_font)
    else:
        for box in node.item_boxes[:12]:
            label = f"{box.box_id}"
            if box.position:
                label += f"  @{box.position[0]},{box.position[1]}"
            y = _render_dim_line(screen, x, y, label, small_font)

    footer = small_font.render("[Enter] open in viewer   [Esc] deselect", True, TEXT_DIM)
    screen.blit(footer, (x, rect.bottom - footer.get_height() - 10))


def _render_edge(
    screen: pygame.Surface,
    rect: pygame.Rect,
    edge: GraphEdge,
    graph: PortalGraph,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    header_font: pygame.font.Font,
) -> None:
    x = rect.left + 14
    y = rect.top + 14

    source_node = graph.nodes_by_id.get(edge.source)
    target_node = graph.nodes_by_id.get(edge.target)
    src_name = source_node.display_name if source_node else edge.source
    dst_name = target_node.display_name if target_node else edge.target

    title = header_font.render("Portal", True, TEXT_HEADER)
    screen.blit(title, (x, y))
    y += title.get_height() + 4

    y = _render_kv(screen, x, y, "from", f"{src_name}  ({edge.source})", font, small_font)
    y = _render_kv(screen, x, y, "to",   f"{dst_name}  ({edge.target})", font, small_font)

    y += SECTION_GAP
    y = _render_section_title(screen, x, y, f"Connections ({len(edge.portals)})", font)
    for i, portal in enumerate(edge.portals, start=1):
        sx, sy = portal.source_tile
        tx, ty = portal.target_tile
        line = f"#{i}: ({sx},{sy})  →  ({tx},{ty})"
        y = _render_dim_line(screen, x, y, line, small_font)

    footer = small_font.render("[Esc] deselect", True, TEXT_DIM)
    screen.blit(footer, (x, rect.bottom - footer.get_height() - 10))


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
) -> int:
    key_label = small_font.render(key, True, TEXT_DIM)
    screen.blit(key_label, (x, y))
    val_label = font.render(_truncate(value, 36), True, TEXT)
    screen.blit(val_label, (x + 80, y - 2))
    return y + max(key_label.get_height(), val_label.get_height()) + 2


def _render_dim_line(
    screen: pygame.Surface, x: int, y: int, text: str, font: pygame.font.Font
) -> int:
    label = font.render(_truncate(text, 44), True, TEXT)
    screen.blit(label, (x + 8, y))
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


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _fit_image(surf: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    sw, sh = surf.get_size()
    scale = min(max_w / sw, max_h / sh, 1.0)
    if scale >= 1.0:
        return surf
    return pygame.transform.smoothscale(surf, (max(1, int(sw * scale)), max(1, int(sh * scale))))
