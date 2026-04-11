# engine/world/tile_map.py

import pytmx
import pygame
from engine.settings import Settings
from engine.world.collision import CollisionMap
from engine.common.portal_data import Portal
from engine.world.portal_loader import PortalLoader


class TileMap:
    """
    Loads a TMX file via pytmx and renders tile layers.
    Exposes collision map and portal list.
    """

    def __init__(
        self,
        tmx_path: str,
        collision_factory=CollisionMap,
        portal_loader: PortalLoader | None = None,
    ) -> None:
        self._tmx = pytmx.load_pygame(tmx_path, pixelalpha=True)
        self.tile_width  = self._tmx.tilewidth
        self.tile_height = self._tmx.tileheight
        self.width       = self._tmx.width     # in tiles
        self.height      = self._tmx.height    # in tiles
        self.collision_map = collision_factory(self._tmx)
        self.portals: list[Portal] = (portal_loader or PortalLoader()).load(self._tmx)

    @property
    def width_px(self) -> int:
        return self.width * self.tile_width

    @property
    def height_px(self) -> int:
        return self.height * self.tile_height

    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        """Render all visible tile layers, culled to viewport."""
        for layer_idx, layer in enumerate(self._tmx.visible_layers):
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            self._render_layer(screen, layer_idx, offset_x, offset_y)

    def _render_layer(
        self,
        screen: pygame.Surface,
        layer_idx: int,
        offset_x: int,
        offset_y: int,
    ) -> None:
        tw = self.tile_width
        th = self.tile_height

        # viewport tile range — cull off-screen tiles
        col_start = max(0, offset_x // tw)
        col_end   = min(self.width,  (offset_x + Settings.SCREEN_WIDTH)  // tw + 1)
        row_start = max(0, offset_y // th)
        row_end   = min(self.height, (offset_y + Settings.SCREEN_HEIGHT) // th + 1)

        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                image = self._tmx.get_tile_image(col, row, layer_idx)
                if image:
                    screen_x = col * tw - offset_x
                    screen_y = row * th - offset_y
                    screen.blit(image, (screen_x, screen_y))