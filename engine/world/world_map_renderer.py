# engine/world/world_map_renderer.py
#
# Rendering for the world map scene — tile map, y-sorted player+NPC drawing,
# overlay rendering, fade overlay, and quit-confirm dialog.

from __future__ import annotations

import pygame

from engine.world.world_map_logic import _is_player_facing


class WorldMapRenderer:
    """Draws the world map: tiles, player, NPCs, overlays, fade, quit dialog."""

    def __init__(self) -> None:
        self._quit_font: pygame.font.Font | None = None

    def render(
        self,
        screen: pygame.Surface,
        tile_map,
        camera,
        player,
        npcs: list,
        overlays: list,
        dialogue,
        fade_alpha: int,
        quit_confirm: bool,
    ) -> None:
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

        drawables = [(player_pos.y, render_player)] + [
            (npc._py, lambda n=npc: render_npc(n)) for npc in npcs
        ]
        for _, draw in sorted(drawables, key=lambda d: d[0]):
            draw()

        for overlay in overlays:
            overlay.render(screen)

        if quit_confirm:
            self._render_quit_confirm(screen)

        if fade_alpha > 0:
            fade_surf = pygame.Surface(
                (screen.get_width(), screen.get_height()), pygame.SRCALPHA
            )
            fade_surf.fill((0, 0, 0, fade_alpha))
            screen.blit(fade_surf, (0, 0))

    def _render_quit_confirm(self, screen: pygame.Surface) -> None:
        if self._quit_font is None:
            self._quit_font = pygame.font.SysFont("Arial", 20, bold=True)
        font = self._quit_font
        hint_font = pygame.font.SysFont("Arial", 16)

        w, h = 320, 110
        x = (screen.get_width() - w) // 2
        y = (screen.get_height() - h) // 2

        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (20, 20, 45), (x, y, w, h))
        pygame.draw.rect(screen, (160, 160, 100), (x, y, w, h), 2)

        title = font.render("Quit Game?", True, (220, 220, 180))
        screen.blit(title, (x + w // 2 - title.get_width() // 2, y + 18))

        hint = hint_font.render("ENTER  confirm       ESC  cancel", True, (160, 160, 120))
        screen.blit(hint, (x + w // 2 - hint.get_width() // 2, y + 68))
