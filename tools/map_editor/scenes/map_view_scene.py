from __future__ import annotations

from pathlib import Path
from typing import Callable

import pygame

from engine.common.scene.scene import Scene
from engine.world.tile_map import TileMap
from tools.map_editor.graph.portal_graph import GraphNode
from tools.map_editor.graph.sprite_cache import SpriteCache
from tools.map_editor.overlay import (
    KIND_ORDER,
    collect_overlay,
    render_legend,
    render_overlay,
)


class MapViewScene(Scene):
    """Renders one TMX with pan (arrows / WASD / drag) and zoom (+/- or wheel)."""

    PAN_SPEED_PX_PER_SEC = 480.0
    MIN_ZOOM = 0.25
    MAX_ZOOM = 4.0
    ZOOM_STEP = 1.25

    def __init__(
        self,
        tmx_path: Path,
        yaml_path: Path | None,
        on_back: Callable[[], None],
        font: pygame.font.Font,
        node: GraphNode,
        sprites: SpriteCache,
    ) -> None:
        self._tmx_path = tmx_path
        self._on_back = on_back
        self._font = font
        self._node = node
        self._sprites = sprites
        self._tile_map = TileMap(str(tmx_path))
        self._cam_x = 0.0
        self._cam_y = 0.0
        self._zoom = 1.0
        self._dragging = False
        self._last_mouse: tuple[int, int] | None = None
        self._overlay = collect_overlay(
            tmx_path=tmx_path,
            yaml_path=yaml_path,
            tile_width=self._tile_map.tile_width,
            tile_height=self._tile_map.tile_height,
        )
        self._visible_kinds: set[str] = set(KIND_ORDER)

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    self._apply_zoom(self.ZOOM_STEP)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self._apply_zoom(1.0 / self.ZOOM_STEP)
                elif event.key in (pygame.K_0, pygame.K_KP_0):
                    self._zoom = 1.0
                elif event.key == pygame.K_BACKSPACE:
                    self._on_back()
                elif event.key == pygame.K_TAB:
                    self._toggle_all_overlay()
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    self._toggle_kind(event.key - pygame.K_1)
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    self._apply_zoom(self.ZOOM_STEP)
                elif event.y < 0:
                    self._apply_zoom(1.0 / self.ZOOM_STEP)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._dragging = True
                self._last_mouse = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging = False
                self._last_mouse = None
            elif event.type == pygame.MOUSEMOTION and self._dragging and self._last_mouse:
                dx = event.pos[0] - self._last_mouse[0]
                dy = event.pos[1] - self._last_mouse[1]
                self._cam_x -= dx / self._zoom
                self._cam_y -= dy / self._zoom
                self._last_mouse = event.pos

    def update(self, delta: float) -> None:
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1.0
        if dx or dy:
            step = self.PAN_SPEED_PX_PER_SEC * delta / self._zoom
            self._cam_x += dx * step
            self._cam_y += dy * step

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((10, 10, 14))

        map_w = self._tile_map.width_px
        map_h = self._tile_map.height_px
        zoomed_w = int(map_w * self._zoom)
        zoomed_h = int(map_h * self._zoom)

        # Render the map at native size to an offscreen surface, then scale once.
        # TileMap.render handles its own offset/clipping via screen.blit.
        if self._zoom == 1.0:
            self._tile_map.render(screen, int(self._cam_x), int(self._cam_y))
        else:
            buf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
            self._tile_map.render(buf, 0, 0)
            scaled = pygame.transform.scale(buf, (zoomed_w, zoomed_h))
            screen.blit(scaled, (-int(self._cam_x * self._zoom), -int(self._cam_y * self._zoom)))

        self._render_sprites(screen)

        render_overlay(
            screen=screen,
            objects=self._overlay,
            visible_kinds=self._visible_kinds,
            cam_x=self._cam_x,
            cam_y=self._cam_y,
            zoom=self._zoom,
            label_font=self._font,
        )

        hud = self._font.render(
            f"{self._tmx_path.stem}   zoom={self._zoom:.2f}   "
            f"({self._tile_map.width}x{self._tile_map.height} tiles)   "
            f"[Backspace=back  +/-=zoom  arrows/WASD=pan  drag=pan  Tab=overlay]",
            True,
            (220, 220, 220),
        )
        bg = pygame.Surface((hud.get_width() + 12, hud.get_height() + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (8, 8))
        screen.blit(hud, (14, 11))

        render_legend(screen=screen, visible_kinds=self._visible_kinds, font=self._font)

    def _render_sprites(self, screen: pygame.Surface) -> None:
        """Blit NPC and item-box sprites at their tile positions.

        Sprites are sized in native map pixels (a 64px character sheet tile
        spans 2 map tiles); they scale with zoom and anchor at the tile's
        top-left, matching the engine's on-map rendering.
        """
        tw = self._tile_map.tile_width
        th = self._tile_map.tile_height

        def _blit(icon: pygame.Surface | None, col: int, row: int) -> None:
            if icon is None:
                return
            dw = max(2, int(icon.get_width() * self._zoom))
            dh = max(2, int(icon.get_height() * self._zoom))
            scaled = pygame.transform.scale(icon, (dw, dh))
            bx = int((col * tw - self._cam_x) * self._zoom)
            by = int((row * th - self._cam_y) * self._zoom)
            if bx + dw < 0 or by + dh < 0 or bx > screen.get_width() or by > screen.get_height():
                return
            screen.blit(scaled, (bx, by))

        for npc in self._node.npcs:
            if npc.position is None:
                continue
            _blit(self._sprites.npc_icon(npc.sprite), npc.position[0], npc.position[1])

        for box in self._node.item_boxes:
            if box.position is None:
                continue
            _blit(self._sprites.item_box_icon(box.sprite), box.position[0], box.position[1])

    def _apply_zoom(self, factor: float) -> None:
        new_zoom = self._zoom * factor
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_zoom))
        # Keep the world point under the mouse pointer fixed on screen.
        mx, my = pygame.mouse.get_pos()
        self._cam_x += mx / self._zoom - mx / new_zoom
        self._cam_y += my / self._zoom - my / new_zoom
        self._zoom = new_zoom

    def _toggle_all_overlay(self) -> None:
        if self._visible_kinds:
            self._visible_kinds = set()
        else:
            self._visible_kinds = set(KIND_ORDER)

    def _toggle_kind(self, index: int) -> None:
        if not 0 <= index < len(KIND_ORDER):
            return
        kind = KIND_ORDER[index]
        if kind in self._visible_kinds:
            self._visible_kinds.discard(kind)
        else:
            self._visible_kinds.add(kind)
