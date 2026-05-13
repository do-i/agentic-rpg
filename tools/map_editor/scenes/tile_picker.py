"""Modal overlay for picking a tile on a map.

Two modes:
  - free: any tile on the map may be picked (used to choose a destination tile).
  - portals: only the listed portal tiles are clickable (used to choose which
    portal on the source map is being retargeted).

Renders the map full-screen with a dim backdrop, shows a hover highlight on the
tile under the cursor, and dispatches a callback with the chosen tile.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import pygame

from tools.map_editor.graph.portal_graph import GraphNode
from tools.map_editor.graph.thumbnails import ThumbnailCache


BACKDROP = (10, 10, 16, 220)
HOVER_FILL = (255, 255, 255, 70)
HOVER_BORDER = (255, 255, 255)
PORTAL_BORDER = (255, 210, 0)
PORTAL_BORDER_HOVER = (255, 255, 120)
PORTAL_FILL = (255, 74, 42, 80)
PORTAL_FILL_HOVER = (255, 200, 80, 140)
HINT_BG = (20, 20, 28, 230)


@dataclass
class PortalOption:
    portal_obj_id: int
    source_tile: tuple[int, int]
    target_map: str
    target_tile: tuple[int, int]


class TilePicker:
    """Modal map view for picking a tile (or a portal) on a single map."""

    def __init__(
        self,
        node: GraphNode,
        thumbnails: ThumbnailCache,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        hint_text: str,
        mode: str,
        on_pick: Callable[[tuple[int, int] | PortalOption | None], None],
        portals: list[PortalOption] | None = None,
    ) -> None:
        if mode not in ("free", "portals"):
            raise ValueError(f"Unknown TilePicker mode: {mode}")
        self._node = node
        self._thumbnails = thumbnails
        self._font = font
        self._small_font = small_font
        self._hint_text = hint_text
        self._mode = mode
        self._on_pick = on_pick
        self._portals = portals or []
        self._hover_tile: tuple[int, int] | None = None
        # Per-frame layout values, recomputed in render.
        self._map_rect: pygame.Rect | None = None

    # ── input ────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the event was consumed by the overlay."""
        if event.type == pygame.MOUSEMOTION:
            self._hover_tile = self._tile_at(event.pos)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            tile = self._tile_at(event.pos)
            if tile is None:
                return True
            if self._mode == "portals":
                match = next(
                    (p for p in self._portals if p.source_tile == tile), None
                )
                # Existing portal → retarget; empty tile → create new portal here.
                self._on_pick(match if match is not None else tile)
            else:
                self._on_pick(tile)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_pick(None)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._on_pick(None)
            return True
        # Swallow all other events while modal so the underlying scene doesn't react.
        return True

    # ── render ───────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, now_ms: int) -> None:
        sw, sh = screen.get_size()
        backdrop = pygame.Surface((sw, sh), pygame.SRCALPHA)
        backdrop.fill(BACKDROP)
        screen.blit(backdrop, (0, 0))

        full = self._thumbnails.get_full(self._node.tmx_path)
        if full is None:
            self._draw_hint(screen, "Could not load map.")
            return

        margin = 32
        max_w = sw - margin * 2
        max_h = sh - margin * 2 - 60  # space for hint bar at top
        scale = min(max_w / full.get_width(), max_h / full.get_height())
        new_w = max(1, int(full.get_width() * scale))
        new_h = max(1, int(full.get_height() * scale))
        if scale > 1.0:
            scaled = pygame.transform.scale(full, (new_w, new_h))
        else:
            scaled = pygame.transform.smoothscale(full, (new_w, new_h))
        map_rect = pygame.Rect(0, 0, new_w, new_h)
        map_rect.centerx = sw // 2
        map_rect.centery = (sh + 40) // 2
        self._map_rect = map_rect
        screen.blit(scaled, map_rect.topleft)

        # Tile size in the rendered map.
        tw, th = self._tile_dims_screen()

        if self._mode == "portals":
            self._draw_portal_options(screen, map_rect, tw, th, now_ms)

        if self._hover_tile is not None:
            self._draw_hover(screen, map_rect, tw, th)

        self._draw_hint(screen, self._hint_text)

    def _draw_portal_options(
        self,
        screen: pygame.Surface,
        map_rect: pygame.Rect,
        tw: float,
        th: float,
        now_ms: int,
    ) -> None:
        pulse = 0.5 + 0.5 * math.sin(now_ms / 220.0)
        for portal in self._portals:
            col, row = portal.source_tile
            rect = pygame.Rect(
                int(map_rect.left + col * tw),
                int(map_rect.top + row * th),
                max(8, int(tw)),
                max(8, int(th)),
            )
            is_hover = self._hover_tile == portal.source_tile
            fill = PORTAL_FILL_HOVER if is_hover else PORTAL_FILL
            border = PORTAL_BORDER_HOVER if is_hover else PORTAL_BORDER
            fill_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            alpha = int(fill[3] * (0.6 + 0.4 * pulse))
            fill_surf.fill((fill[0], fill[1], fill[2], alpha))
            screen.blit(fill_surf, rect.topleft)
            pygame.draw.rect(screen, border, rect, width=2)
            label = self._small_font.render(
                f"#{portal.portal_obj_id} → {portal.target_map}", True, (255, 255, 255)
            )
            bg = pygame.Surface(
                (label.get_width() + 8, label.get_height() + 4), pygame.SRCALPHA
            )
            bg.fill((20, 20, 28, 220))
            bg_pos = (rect.left, rect.top - bg.get_height() - 2)
            screen.blit(bg, bg_pos)
            screen.blit(label, (bg_pos[0] + 4, bg_pos[1] + 2))

    def _draw_hover(
        self, screen: pygame.Surface, map_rect: pygame.Rect, tw: float, th: float
    ) -> None:
        col, row = self._hover_tile
        rect = pygame.Rect(
            int(map_rect.left + col * tw),
            int(map_rect.top + row * th),
            max(6, int(tw)),
            max(6, int(th)),
        )
        fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        fill.fill(HOVER_FILL)
        screen.blit(fill, rect.topleft)
        pygame.draw.rect(screen, HOVER_BORDER, rect, width=2)
        coord_label = self._small_font.render(
            f"({col}, {row})", True, (255, 255, 255)
        )
        bg = pygame.Surface(
            (coord_label.get_width() + 8, coord_label.get_height() + 4), pygame.SRCALPHA
        )
        bg.fill((20, 20, 28, 220))
        bg_pos = (rect.right + 4, rect.top)
        screen.blit(bg, bg_pos)
        screen.blit(coord_label, (bg_pos[0] + 4, bg_pos[1] + 2))

    def _draw_hint(self, screen: pygame.Surface, text: str) -> None:
        label = self._font.render(text, True, (240, 240, 240))
        sub = self._small_font.render(
            "[Esc / Right-click] cancel", True, (180, 180, 200)
        )
        sw, _ = screen.get_size()
        bg = pygame.Surface(
            (max(label.get_width(), sub.get_width()) + 24, label.get_height() + sub.get_height() + 14),
            pygame.SRCALPHA,
        )
        bg.fill(HINT_BG)
        x = sw // 2 - bg.get_width() // 2
        y = 12
        screen.blit(bg, (x, y))
        screen.blit(label, (x + 12, y + 6))
        screen.blit(sub, (x + 12, y + 6 + label.get_height() + 2))

    # ── helpers ──────────────────────────────────────────────────────────

    def _tile_dims_screen(self) -> tuple[float, float]:
        map_w_px, map_h_px = self._node.map_size_px
        tile_w_px, tile_h_px = self._node.tile_size_px
        if self._map_rect is None or map_w_px == 0 or map_h_px == 0:
            return 1.0, 1.0
        return (
            self._map_rect.width * tile_w_px / map_w_px,
            self._map_rect.height * tile_h_px / map_h_px,
        )

    def _tile_at(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if self._map_rect is None or not self._map_rect.collidepoint(pos):
            return None
        tw, th = self._tile_dims_screen()
        if tw <= 0 or th <= 0:
            return None
        col = int((pos[0] - self._map_rect.left) // tw)
        row = int((pos[1] - self._map_rect.top) // th)
        return (col, row)
