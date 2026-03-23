# engine/world/portal_loader.py

import pytmx
from engine.world.portal import Portal
from engine.core.models.position import Position

PORTAL_LAYER_NAME = "portals"


class PortalLoader:
    """
    Reads the 'portals' object layer from a loaded TMX map.
    Each object must have custom properties:
        target_map          (str)
        target_position_x   (int)
        target_position_y   (int)
    """

    def load(self, tmx_data: pytmx.TiledMap) -> list[Portal]:
        portals = []
        for layer in tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            if layer.name != PORTAL_LAYER_NAME:
                continue
            for obj in layer:
                portal = self._parse(obj)
                if portal:
                    portals.append(portal)
        return portals

    def _parse(self, obj) -> Portal | None:
        props = obj.properties or {}
        target_map = props.get("target_map")
        target_x   = props.get("target_position_x")
        target_y   = props.get("target_position_y")

        if not target_map or target_x is None or target_y is None:
            return None

        return Portal(
            x=int(obj.x),
            y=int(obj.y),
            width=int(obj.width or 0),
            height=int(obj.height or 0),
            target_map=target_map,
            target_position=Position(target_x, target_y),
        )