# engine/world/tile_map.py

import pytmx
import pygame
from engine.world.collision import CollisionMap
from engine.world.portal_data import Portal
from engine.world.portal_loader import PortalLoader

SPAWN_TILE_LAYER = "spawn_tile"   # tile layer: any placed tile = spawn point
BOSS_ENEMY_LAYER = "boss_enemy"   # object group: single object = boss spawn position


def _load_enemy_spawn_tiles(tmx_data: pytmx.TiledMap) -> list[dict]:
    """
    Return spawn points as [{x, y}] in pixel coords.
    Reads the 'spawn_tile' tile layer — each placed tile is one spawn point.
    """
    tw = tmx_data.tilewidth
    th = tmx_data.tileheight
    for layer in tmx_data.layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue
        if layer.name != SPAWN_TILE_LAYER:
            continue
        tiles = []
        for x, y, gid in layer:
            if gid:  # 0 = empty; any non-zero GID = spawn point
                tiles.append({"x": x * tw, "y": y * th})
        return tiles
    return []


def _load_boss_spawn_tile(tmx_data: pytmx.TiledMap) -> dict | None:
    """
    Read the first object in the 'boss_enemy' object group.
    Returns {x, y, is_boss: True} in pixel coords snapped to tile grid, or None.
    """
    tw = tmx_data.tilewidth
    th = tmx_data.tileheight
    for layer in tmx_data.layers:
        if not isinstance(layer, pytmx.TiledObjectGroup):
            continue
        if layer.name != BOSS_ENEMY_LAYER:
            continue
        for obj in layer:
            # Snap the object's pixel position to the nearest tile boundary
            x = round(obj.x / tw) * tw
            y = round(obj.y / th) * th
            return {"x": x, "y": y, "is_boss": True}
    return None


class TileMap:
    """
    Loads a TMX file via pytmx and renders tile layers.
    Exposes collision map, portal list, and enemy spawn tiles.
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
        self.collision_map = collision_factory(self._tmx, self._tmx.tilewidth)
        self.portals: list[Portal] = (portal_loader or PortalLoader()).load(self._tmx)
        self.enemy_spawn_tiles: list[dict] = _load_enemy_spawn_tiles(self._tmx)
        self.boss_spawn_tile: dict | None = _load_boss_spawn_tile(self._tmx)

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
        col_end   = min(self.width,  (offset_x + screen.get_width())  // tw + 1)
        row_start = max(0, offset_y // th)
        row_end   = min(self.height, (offset_y + screen.get_height()) // th + 1)

        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                image = self._tmx.get_tile_image(col, row, layer_idx)
                if image:
                    screen_x = col * tw - offset_x
                    screen_y = row * th - offset_y
                    screen.blit(image, (screen_x, screen_y))