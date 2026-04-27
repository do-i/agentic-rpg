# engine/world/world_map_overlays.py
#
# Holds the seven overlay slots a WorldMapScene can stack on top of itself
# (dialogue, save modal, magic-core shop, inn, item shop, apothecary, item-box
# modal) and routes events/update/render to whichever is on top.
from __future__ import annotations

from engine.dialogue.dialogue_scene import DialogueScene
from engine.inn.inn_scene import InnScene
from engine.shop.apothecary_scene import ApothecaryScene
from engine.shop.item_shop_scene import ItemShopScene
from engine.shop.magic_core_shop_scene import MagicCoreShopScene
from engine.title.save_modal_scene import SaveModalScene
from engine.world.item_box_scene import ItemBoxScene


class WorldMapOverlays:
    """Container for the world-map overlay slots plus helpers for routing.

    Only one overlay is typically open at a time. The `active` property
    returns whichever slot currently owns input/update — dialogue takes
    precedence over the modals, matching the previous explicit chain.
    """

    def __init__(self) -> None:
        self.save_modal: SaveModalScene | None = None
        self.dialogue: DialogueScene | None = None
        self.mc_shop: MagicCoreShopScene | None = None
        self.inn: InnScene | None = None
        self.item_shop: ItemShopScene | None = None
        self.apothecary: ApothecaryScene | None = None
        self.item_box_modal: ItemBoxScene | None = None

    def reset(self) -> None:
        self.save_modal = None
        self.dialogue = None
        self.mc_shop = None
        self.inn = None
        self.item_shop = None
        self.apothecary = None
        self.item_box_modal = None

    @property
    def active(self):
        """The overlay that owns input/update right now, or None."""
        for overlay in (
            self.dialogue,
            self.save_modal,
            self.mc_shop,
            self.inn,
            self.item_shop,
            self.apothecary,
            self.item_box_modal,
        ):
            if overlay is not None:
                return overlay
        return None

    @property
    def any_active(self) -> bool:
        return self.active is not None

    def render_list(self) -> list:
        """Overlays to render this frame, in back-to-front order."""
        return [
            overlay for overlay in (
                self.save_modal,
                self.dialogue,
                self.mc_shop,
                self.inn,
                self.item_shop,
                self.apothecary,
                self.item_box_modal,
            ) if overlay is not None
        ]
