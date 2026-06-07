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
from tools.map_editor.graph.sprite_cache import SpriteCache
from tools.map_editor.graph.thumbnails import ThumbnailCache


BACKDROP = (10, 10, 16, 220)
HOVER_FILL = (255, 255, 255, 70)
HOVER_BORDER = (255, 255, 255)
PORTAL_BORDER = (255, 210, 0)
PORTAL_BORDER_HOVER = (255, 255, 120)
PORTAL_FILL = (255, 74, 42, 80)
PORTAL_FILL_HOVER = (255, 200, 80, 140)
DRAG_RECT_FILL = (80, 200, 255, 90)
DRAG_RECT_BORDER = (120, 220, 255)
HINT_BG = (20, 20, 28, 230)

# Below this pixel movement a drag is treated as a plain click.
DRAG_CLICK_THRESHOLD_PX = 5


@dataclass
class PortalOption:
    portal_obj_id: int
    source_tile: tuple[int, int]
    source_rect_px: tuple[int, int, int, int]   # (x, y, w, h) in map pixels
    target_map: str
    target_tile: tuple[int, int]


@dataclass
class PortalPick:
    """Result of choosing a portal area on the source map.

    `existing` is the portal being retargeted, or None to create a new one.
    `source_rect_px` is the geometry to write (x, y, w, h in map pixels), or
    None to keep an existing portal's current geometry (plain click retarget).
    """
    existing: PortalOption | None
    source_tile: tuple[int, int]
    source_rect_px: tuple[int, int, int, int] | None


class TilePicker:
    """Modal map view for picking a tile (or a portal) on a single map."""

    def __init__(
        self,
        node: GraphNode,
        thumbnails: ThumbnailCache,
        sprites: SpriteCache,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        hint_text: str,
        mode: str,
        on_pick: Callable[[tuple[int, int] | PortalPick | None], None],
        portals: list[PortalOption] | None = None,
    ) -> None:
        if mode not in ("free", "portals"):
            raise ValueError(f"Unknown TilePicker mode: {mode}")
        self._node = node
        self._thumbnails = thumbnails
        self._sprites = sprites
        self._font = font
        self._small_font = small_font
        self._hint_text = hint_text
        self._mode = mode
        self._on_pick = on_pick
        self._portals = portals or []
        self._hover_tile: tuple[int, int] | None = None
        # Drag-to-select-area state (portals mode), in map pixels.
        self._drag_start_px: tuple[float, float] | None = None
        self._drag_cur_px: tuple[float, float] | None = None
        self._drag_start_screen: tuple[int, int] | None = None
        self._drag_on_existing: PortalOption | None = None
        # Per-frame layout values, recomputed in render.
        self._map_rect: pygame.Rect | None = None

    # ── input ────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the event was consumed by the overlay."""
        if event.type == pygame.MOUSEMOTION:
            self._hover_tile = self._tile_at(event.pos)
            if self._drag_start_px is not None:
                self._drag_cur_px = self._map_px_at(event.pos, clamp=True)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._mode == "portals":
                self._begin_drag(event.pos)
            else:
                tile = self._tile_at(event.pos)
                if tile is not None:
                    self._on_pick(tile)
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._mode == "portals" and self._drag_start_px is not None:
                self._finish_drag(event.pos)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_pick(None)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._on_pick(None)
            return True
        # Swallow all other events while modal so the underlying scene doesn't react.
        return True

    def _begin_drag(self, pos: tuple[int, int]) -> None:
        start = self._map_px_at(pos, clamp=False)
        if start is None:
            return
        self._drag_start_px = start
        self._drag_cur_px = start
        self._drag_start_screen = pos
        self._drag_on_existing = self._portal_at_px(start)

    def _finish_drag(self, pos: tuple[int, int]) -> None:
        start_screen = self._drag_start_screen
        existing = self._drag_on_existing
        start_px = self._drag_start_px
        cur_px = self._map_px_at(pos, clamp=True) or self._drag_cur_px or start_px
        self._reset_drag()
        if start_px is None or start_screen is None:
            return

        moved = abs(pos[0] - start_screen[0]) + abs(pos[1] - start_screen[1])
        if moved < DRAG_CLICK_THRESHOLD_PX:
            # Plain click: retarget an existing portal (keep geometry) or add a
            # new one-tile portal at the clicked tile.
            if existing is not None:
                self._on_pick(PortalPick(existing, existing.source_tile, None))
                return
            tile = self._tile_at(start_screen)
            if tile is None:
                return
            self._on_pick(PortalPick(None, tile, self._tile_rect_px(tile)))
            return

        # Drag: build the selected rect in map pixels.
        rect_px = self._normalized_rect_px(start_px, cur_px)
        top_left_tile = self._tile_of_px(rect_px[0], rect_px[1])
        # Existing portal under the drag start → resize + retarget; else new.
        self._on_pick(PortalPick(existing, top_left_tile, rect_px))

    def _reset_drag(self) -> None:
        self._drag_start_px = None
        self._drag_cur_px = None
        self._drag_start_screen = None
        self._drag_on_existing = None

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

        # Overlay NPC + item-box sprites so the user can see actor positions in context.
        self._draw_actor_sprites(screen, map_rect)

        # Tile size in the rendered map.
        tw, th = self._tile_dims_screen()

        if self._mode == "portals":
            self._draw_portal_options(screen, map_rect, now_ms)

        if self._hover_tile is not None and self._drag_start_px is None:
            self._draw_hover(screen, map_rect, tw, th)

        if self._drag_start_px is not None and self._drag_cur_px is not None:
            self._draw_drag_rect(screen)

        self._draw_hint(screen, self._hint_text)

    def _draw_actor_sprites(self, screen: pygame.Surface, map_rect: pygame.Rect) -> None:
        map_w_px, map_h_px = self._node.map_size_px
        tile_w_px, tile_h_px = self._node.tile_size_px
        if map_w_px <= 0 or map_h_px <= 0:
            return
        sx = map_rect.width / map_w_px
        sy = map_rect.height / map_h_px

        def _blit(icon, col: int, row: int) -> None:
            if icon is None:
                return
            # Sprites are sized in native map pixels (a 64px character sheet
            # tile spans 2 map tiles); scale by the map→screen ratio and anchor
            # at the tile's top-left to match the engine. Squashing to one
            # screen tile would mis-place 2-tile-tall sprites by a tile.
            dw = max(4, int(icon.get_width() * sx))
            dh = max(4, int(icon.get_height() * sy))
            scaled = pygame.transform.smoothscale(icon, (dw, dh))
            bx = map_rect.left + int(col * tile_w_px * sx)
            by = map_rect.top + int(row * tile_h_px * sy)
            screen.blit(scaled, (bx, by))

        for npc in self._node.npcs:
            if npc.position is None:
                continue
            _blit(self._sprites.npc_icon(npc.sprite), npc.position[0], npc.position[1])
        for box in self._node.item_boxes:
            if box.position is None:
                continue
            _blit(self._sprites.item_box_icon(box.sprite), box.position[0], box.position[1])

    def _draw_portal_options(
        self,
        screen: pygame.Surface,
        map_rect: pygame.Rect,
        now_ms: int,
    ) -> None:
        pulse = 0.5 + 0.5 * math.sin(now_ms / 220.0)
        mouse_pos = pygame.mouse.get_pos()
        for portal in self._portals:
            rect = self._screen_rect_from_px(portal.source_rect_px)
            if rect is None:
                continue
            is_hover = rect.collidepoint(mouse_pos)
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

    def _draw_drag_rect(self, screen: pygame.Surface) -> None:
        rect_px = self._normalized_rect_px(self._drag_start_px, self._drag_cur_px)
        rect = self._screen_rect_from_px(rect_px)
        if rect is None:
            return
        fill_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        fill_surf.fill(DRAG_RECT_FILL)
        screen.blit(fill_surf, rect.topleft)
        pygame.draw.rect(screen, DRAG_RECT_BORDER, rect, width=2)
        x, y, w, h = rect_px
        info = self._small_font.render(
            f"{w}x{h}px  @{x},{y}", True, (255, 255, 255)
        )
        bg = pygame.Surface(
            (info.get_width() + 8, info.get_height() + 4), pygame.SRCALPHA
        )
        bg.fill((20, 20, 28, 220))
        screen.blit(bg, (rect.left, rect.bottom + 2))
        screen.blit(info, (rect.left + 4, rect.bottom + 4))

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

    def _map_px_at(
        self, pos: tuple[int, int], clamp: bool
    ) -> tuple[float, float] | None:
        """Convert a screen position to map-pixel coordinates.

        With clamp=False, returns None for positions outside the map; with
        clamp=True, clamps into the map bounds (so a drag can run to the edge).
        """
        map_w_px, map_h_px = self._node.map_size_px
        if self._map_rect is None or map_w_px == 0 or map_h_px == 0:
            return None
        if not clamp and not self._map_rect.collidepoint(pos):
            return None
        fx = (pos[0] - self._map_rect.left) * map_w_px / self._map_rect.width
        fy = (pos[1] - self._map_rect.top) * map_h_px / self._map_rect.height
        fx = max(0.0, min(float(map_w_px), fx))
        fy = max(0.0, min(float(map_h_px), fy))
        return (fx, fy)

    def _tile_of_px(self, x: float, y: float) -> tuple[int, int]:
        tile_w_px, tile_h_px = self._node.tile_size_px
        return (int(x // max(1, tile_w_px)), int(y // max(1, tile_h_px)))

    def _tile_rect_px(self, tile: tuple[int, int]) -> tuple[int, int, int, int]:
        tile_w_px, tile_h_px = self._node.tile_size_px
        col, row = tile
        return (col * tile_w_px, row * tile_h_px, tile_w_px, tile_h_px)

    def _normalized_rect_px(
        self, a: tuple[float, float], b: tuple[float, float]
    ) -> tuple[int, int, int, int]:
        x0, y0 = a
        x1, y1 = b
        x, y = int(min(x0, x1)), int(min(y0, y1))
        w = max(1, int(abs(x1 - x0)))
        h = max(1, int(abs(y1 - y0)))
        return (x, y, w, h)

    def _portal_at_px(
        self, px: tuple[float, float]
    ) -> PortalOption | None:
        """The topmost existing portal whose geometry contains the point."""
        for portal in reversed(self._portals):
            x, y, w, h = portal.source_rect_px
            if x <= px[0] <= x + w and y <= px[1] <= y + h:
                return portal
        return None

    def _screen_rect_from_px(
        self, rect_px: tuple[int, int, int, int]
    ) -> pygame.Rect | None:
        map_w_px, map_h_px = self._node.map_size_px
        if self._map_rect is None or map_w_px == 0 or map_h_px == 0:
            return None
        sx = self._map_rect.width / map_w_px
        sy = self._map_rect.height / map_h_px
        x, y, w, h = rect_px
        return pygame.Rect(
            int(self._map_rect.left + x * sx),
            int(self._map_rect.top + y * sy),
            max(6, int(w * sx)),
            max(6, int(h * sy)),
        )
