# engine/world/world_map_renderer.py
#
# Rendering for the world map scene — tile map, y-sorted player+NPC+enemy drawing,
# overlay rendering, fade overlay, and quit-confirm dialog.

from __future__ import annotations

import pygame

from engine.world.world_map_logic import _is_player_facing
from engine.common.font_provider import get_fonts


class WorldMapRenderer:
    """Draws the world map: tiles, player, NPCs, enemy sprites, overlays, fade, quit dialog."""

    def __init__(self) -> None:
        self._quit_font: pygame.font.Font | None = None
        # Reusable full-screen overlays. Allocated lazily on first use; the
        # screen size is fixed at runtime so we only ever build one of each.
        self._fade_surf: pygame.Surface | None = None
        self._quit_dim_surf: pygame.Surface | None = None

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
        quit_confirm: bool,
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

        if quit_confirm:
            self._render_quit_confirm(screen)

        if fade_alpha > 0:
            if self._fade_surf is None:
                self._fade_surf = pygame.Surface(
                    (screen.get_width(), screen.get_height()), pygame.SRCALPHA
                )
            self._fade_surf.fill((0, 0, 0, fade_alpha))
            screen.blit(self._fade_surf, (0, 0))

    def _render_portal_debug(self, screen: pygame.Surface, tile_map, camera) -> None:
        for portal in tile_map.portals:
            w = portal.width if portal.width > 0 else 4
            h = portal.height if portal.height > 0 else 4
            x = portal.x - camera.offset_x
            y = portal.y - camera.offset_y
            pygame.draw.rect(screen, (0, 200, 255), (x, y, w, h), 2)

    def _render_quit_confirm(self, screen: pygame.Surface) -> None:
        if self._quit_font is None:
            self._quit_font = get_fonts().get(20, bold=True)
        font = self._quit_font
        hint_font = get_fonts().get(16)

        w, h = 320, 110
        x = (screen.get_width() - w) // 2
        y = (screen.get_height() - h) // 2

        if self._quit_dim_surf is None:
            self._quit_dim_surf = pygame.Surface(
                (screen.get_width(), screen.get_height()), pygame.SRCALPHA
            )
            self._quit_dim_surf.fill((0, 0, 0, 160))
        screen.blit(self._quit_dim_surf, (0, 0))

        pygame.draw.rect(screen, (20, 20, 45), (x, y, w, h))
        pygame.draw.rect(screen, (160, 160, 100), (x, y, w, h), 2)

        title = font.render("Quit Game?", True, (220, 220, 180))
        screen.blit(title, (x + w // 2 - title.get_width() // 2, y + 18))

        hint = hint_font.render("ENTER  confirm       ESC  cancel", True, (160, 160, 120))
        screen.blit(hint, (x + w // 2 - hint.get_width() // 2, y + 68))
