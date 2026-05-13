"""Collects overlay objects (portals, NPCs, item boxes, spawn points, etc.)
from a TMX map and its matching scenario map YAML.

This module is read-only — it builds an in-memory list of OverlayObjects
for the viewer to draw on top of the rendered tile map.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame
import pytmx
import yaml


# Object kinds. Keeping these as strings keeps the renderer decoupled from
# any class hierarchy — the kind is a tag for color + filter, nothing more.
KIND_PORTAL       = "portal"
KIND_BOSS_SPAWN   = "boss_spawn"
KIND_ENEMY_SPAWN  = "enemy_spawn"
KIND_NPC          = "npc"
KIND_ITEM_BOX     = "item_box"
KIND_INN          = "inn"

KIND_ORDER: tuple[str, ...] = (
    KIND_PORTAL,
    KIND_BOSS_SPAWN,
    KIND_ENEMY_SPAWN,
    KIND_NPC,
    KIND_ITEM_BOX,
    KIND_INN,
)

KIND_COLORS: dict[str, tuple[int, int, int]] = {
    KIND_PORTAL:      (80, 200, 240),   # cyan
    KIND_BOSS_SPAWN:  (240, 80, 80),    # red
    KIND_ENEMY_SPAWN: (240, 160, 60),   # orange
    KIND_NPC:         (120, 220, 120),  # green
    KIND_ITEM_BOX:    (240, 220, 90),   # yellow
    KIND_INN:         (160, 140, 240),  # purple
}


@dataclass(frozen=True)
class OverlayObject:
    kind: str
    # Native (unzoomed) pixel coordinates on the map.
    x_px: int
    y_px: int
    w_px: int
    h_px: int
    label: str


def collect_overlay(
    tmx_path: Path,
    yaml_path: Path | None,
    tile_width: int,
    tile_height: int,
) -> list[OverlayObject]:
    """Build the overlay list for one map.

    Loads the TMX again (cheap: pytmx caches images globally) to read object
    layers without going through the engine's loaders, which insist on a full
    pygame display + sprite-sheet cache.
    """
    tmx = pytmx.load_pygame(str(tmx_path), pixelalpha=True)
    out: list[OverlayObject] = []
    out.extend(_collect_portals(tmx))
    out.extend(_collect_boss_spawn(tmx, tile_width, tile_height))
    out.extend(_collect_enemy_spawn(tmx, tile_width, tile_height))
    if yaml_path is not None:
        out.extend(_collect_from_yaml(yaml_path, tile_width, tile_height))
    return out


def _collect_portals(tmx: pytmx.TiledMap) -> list[OverlayObject]:
    found: list[OverlayObject] = []
    for layer in tmx.layers:
        if not isinstance(layer, pytmx.TiledObjectGroup):
            continue
        if layer.name != "portals":
            continue
        for obj in layer:
            props = obj.properties or {}
            target = props.get("target_map", "?")
            tx = props.get("target_position_x", "?")
            ty = props.get("target_position_y", "?")
            found.append(
                OverlayObject(
                    kind=KIND_PORTAL,
                    x_px=int(obj.x),
                    y_px=int(obj.y),
                    w_px=int(obj.width or 0),
                    h_px=int(obj.height or 0),
                    label=f"→ {target} ({tx},{ty})",
                )
            )
    return found


def _collect_boss_spawn(
    tmx: pytmx.TiledMap, tw: int, th: int
) -> list[OverlayObject]:
    for layer in tmx.layers:
        if not isinstance(layer, pytmx.TiledObjectGroup):
            continue
        if layer.name != "boss_enemy":
            continue
        for obj in layer:
            x = round(obj.x / tw) * tw
            y = round(obj.y / th) * th
            return [
                OverlayObject(
                    kind=KIND_BOSS_SPAWN,
                    x_px=int(x),
                    y_px=int(y),
                    w_px=tw,
                    h_px=th,
                    label="boss",
                )
            ]
    return []


def _collect_enemy_spawn(
    tmx: pytmx.TiledMap, tw: int, th: int
) -> list[OverlayObject]:
    found: list[OverlayObject] = []
    for layer in tmx.layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue
        if layer.name != "spawn_tile":
            continue
        for x, y, gid in layer:
            if gid:
                found.append(
                    OverlayObject(
                        kind=KIND_ENEMY_SPAWN,
                        x_px=x * tw,
                        y_px=y * th,
                        w_px=tw,
                        h_px=th,
                        label="spawn",
                    )
                )
    return found


def _collect_from_yaml(
    yaml_path: Path, tw: int, th: int
) -> list[OverlayObject]:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    found: list[OverlayObject] = []

    for entry in data.get("npcs") or []:
        pos = entry.get("position")
        if not pos:
            continue
        found.append(
            OverlayObject(
                kind=KIND_NPC,
                x_px=int(pos[0]) * tw,
                y_px=int(pos[1]) * th,
                w_px=tw,
                h_px=th,
                label=str(entry.get("name") or entry.get("id") or "npc"),
            )
        )

    for entry in data.get("item_boxes") or []:
        pos = entry.get("position")
        if not pos:
            continue
        found.append(
            OverlayObject(
                kind=KIND_ITEM_BOX,
                x_px=int(pos[0]) * tw,
                y_px=int(pos[1]) * th,
                w_px=tw,
                h_px=th,
                label=str(entry.get("id") or "box"),
            )
        )

    inn = data.get("inn")
    if isinstance(inn, dict) and "position" in inn:
        pos = inn["position"]
        found.append(
            OverlayObject(
                kind=KIND_INN,
                x_px=int(pos[0]) * tw,
                y_px=int(pos[1]) * th,
                w_px=tw,
                h_px=th,
                label=f"inn ({inn.get('cost', '?')}g)",
            )
        )

    return found


def render_overlay(
    screen: pygame.Surface,
    objects: list[OverlayObject],
    visible_kinds: set[str],
    cam_x: float,
    cam_y: float,
    zoom: float,
    label_font: pygame.font.Font,
) -> None:
    """Draw rectangles, outlines, and labels for each visible overlay object.

    Rectangles scale with zoom (so they sit on the right tiles). Labels are
    drawn at the font's native pixel size (scaling labels with zoom makes them
    unreadable at extremes).
    """
    for obj in objects:
        if obj.kind not in visible_kinds:
            continue
        color = KIND_COLORS[obj.kind]
        sx = int((obj.x_px - cam_x) * zoom)
        sy = int((obj.y_px - cam_y) * zoom)
        sw = max(2, int(obj.w_px * zoom))
        sh = max(2, int(obj.h_px * zoom))

        if sx + sw < 0 or sy + sh < 0 or sx > screen.get_width() or sy > screen.get_height():
            continue

        fill = pygame.Surface((sw, sh), pygame.SRCALPHA)
        fill.fill((*color, 70))
        screen.blit(fill, (sx, sy))
        pygame.draw.rect(screen, color, (sx, sy, sw, sh), width=2)

        label = label_font.render(obj.label, True, color)
        label_bg = pygame.Surface(
            (label.get_width() + 4, label.get_height() + 2), pygame.SRCALPHA
        )
        label_bg.fill((0, 0, 0, 170))
        screen.blit(label_bg, (sx, sy - label.get_height() - 2))
        screen.blit(label, (sx + 2, sy - label.get_height() - 1))


def render_legend(
    screen: pygame.Surface,
    visible_kinds: set[str],
    font: pygame.font.Font,
) -> None:
    """Draw the kind legend in the lower-left, showing on/off state."""
    line_h = font.get_linesize()
    margin = 10
    panel_w = 220
    panel_h = line_h * (len(KIND_ORDER) + 1) + 12
    panel_x = margin
    panel_y = screen.get_height() - panel_h - margin

    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 170))
    screen.blit(panel, (panel_x, panel_y))

    header = font.render("Overlay  (Tab=all, 1-6=toggle)", True, (220, 220, 220))
    screen.blit(header, (panel_x + 8, panel_y + 4))

    for i, kind in enumerate(KIND_ORDER):
        y = panel_y + 4 + line_h * (i + 1)
        on = kind in visible_kinds
        color = KIND_COLORS[kind] if on else (90, 90, 90)
        pygame.draw.rect(screen, color, (panel_x + 8, y + 4, 14, 10))
        prefix = f"{i + 1}."
        text = f"{prefix} {kind}{'' if on else '  (off)'}"
        screen.blit(font.render(text, True, color), (panel_x + 30, y))
