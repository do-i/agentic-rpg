# engine/world/world_map_renderer.py
#
# Rendering for the world map scene — tile map, y-sorted player+NPC+enemy drawing,
# overlay rendering, and fade overlay.

from __future__ import annotations

import pygame

from engine.world.world_map_logic import _is_player_facing


class WorldMapRenderer:
    """Draws the world map: tiles, player, NPCs, enemy sprites, overlays, fade."""

    def __init__(self) -> None:
        # Reusable full-screen overlays. Allocated lazily on first use; the
        # screen size is fixed at runtime so we only ever build one of each.
        self._fade_surf: pygame.Surface | None = None
        self._fade_surf_alpha: int = -1

    def render(
        self,
        screen: pygame.Surface,
        tile_map,
        camera,
        player,
        npcs: list,
        enemy_sprites: list,
        overlays: list,
        dialogue,
        fade_alpha: int,
        item_boxes: list | None = None,
        box_opened: dict | None = None,
        debug_collision: bool = False,
    ) -> None:
        item_boxes = item_boxes or []
        box_opened = box_opened or {}

        screen.fill((0, 0, 0))
        tile_map.render(screen, camera.offset_x, camera.offset_y)

        player_pos = player.pixel_position

        def render_player():
            player.render(screen, camera.offset_x, camera.offset_y)

        def render_npc(npc):
            near = (npc.is_near(player_pos)
                    and npc.is_facing_toward(player_pos)
                    and _is_player_facing(player, npc.pixel_position)
                    and dialogue is None)
            npc.render(
                screen,
                camera.offset_x,
                camera.offset_y,
                near=near,
                player_pos=player_pos,
            )

        def render_enemy(sprite):
            sprite.render(screen, camera.offset_x, camera.offset_y)

        def render_box(box):
            near = (box.is_near(player_pos)
                    and _is_player_facing(player, box.pixel_position)
                    and dialogue is None)
            box.render(
                screen,
                camera.offset_x,
                camera.offset_y,
                opened=box_opened.get(box.id, False),
                near=near,
            )

        # Sort by bottom-of-sprite so tall (64px) entities and short (32px)
        # chests interleave correctly.
        drawables = [(player.sort_y, render_player)]
        drawables += [(npc.sort_y, lambda n=npc: render_npc(n)) for npc in npcs]
        drawables += [(e.sort_y, lambda s=e: render_enemy(s)) for e in enemy_sprites]
        drawables += [(b.sort_y, lambda bx=b: render_box(bx)) for b in item_boxes]

        for _, draw in sorted(drawables, key=lambda d: d[0]):
            draw()

        if debug_collision:
            self._render_portal_debug(screen, tile_map, camera)

        for overlay in overlays:
            overlay.render(screen)

        if fade_alpha > 0:
            if self._fade_surf is None:
                self._fade_surf = pygame.Surface(
                    (screen.get_width(), screen.get_height()), pygame.SRCALPHA
                )
            if self._fade_surf_alpha != fade_alpha:
                self._fade_surf.fill((0, 0, 0, fade_alpha))
                self._fade_surf_alpha = fade_alpha
            screen.blit(self._fade_surf, (0, 0))

    def _render_portal_debug(self, screen: pygame.Surface, tile_map, camera) -> None:
        for portal in tile_map.portals:
            w = portal.width if portal.width > 0 else 4
            h = portal.height if portal.height > 0 else 4
            x = portal.x - camera.offset_x
            y = portal.y - camera.offset_y
            pygame.draw.rect(screen, (0, 200, 255), (x, y, w, h), 2)
