# engine/world/item_box_loader.py

from pathlib import Path

from engine.io.manifest_loader import ManifestLoader
from engine.io.yaml_loader import load_yaml_optional
from engine.world.item_box import ItemBox
from engine.world.item_box_sprite import ItemBoxSprite

VALID_MC_SIZES = {"xs", "s", "m", "l", "xl"}


class ItemBoxLoader:
    """
    Reads item_boxes from a map YAML file and returns ItemBox instances.
    The sprite is scenario-wide (declared once in manifest.item_box.sprite)
    and shared across every ItemBox instance the loader produces.
    """

    def __init__(
        self,
        manifest_loader: ManifestLoader,
        tile_size: int,
    ) -> None:
        self._scenario_path = manifest_loader.scenario_path
        self._tile_size = tile_size
        self._sprite = self._load_shared_sprite(manifest_loader.load())

    def _load_shared_sprite(self, manifest: dict) -> ItemBoxSprite | None:
        cfg = manifest.get("item_box") or {}
        sprite_rel = cfg.get("sprite")
        if not sprite_rel:
            return None
        full_path = self._scenario_path / sprite_rel
        if not full_path.exists():
            print(f"[WARN] item_box sprite not found: {full_path}")
            return None
        try:
            return ItemBoxSprite(full_path)
        except Exception as e:
            print(f"[WARN] failed to load item_box sprite {full_path}: {e}")
            return None

    def load_from_map(self, map_yaml_path: Path) -> list[ItemBox]:
        return self.parse_from_map_data(load_yaml_optional(map_yaml_path))

    def parse_from_map_data(self, data: dict | None) -> list[ItemBox]:
        """Build ItemBox instances from already-parsed map YAML data.

        Used by world_map_init when the file has already been loaded so we
        don't re-read the same path through every loader.
        """
        if not isinstance(data, dict):
            return []
        return [self._parse(entry) for entry in data.get("item_boxes", [])]

    def _parse(self, entry: dict) -> ItemBox:
        for key in ("id", "position"):
            if key not in entry:
                raise KeyError(
                    f"item_box entry missing required field {key!r}: {entry!r}"
                )
        box_id = entry["id"]
        position = entry["position"]
        present = entry.get("present", {}) or {}
        loot = entry.get("loot", {}) or {}

        loot_items: list[tuple[str, int]] = [
            (item["id"], int(item.get("qty", 1)))
            for item in (loot.get("items") or [])
        ]
        loot_magic_cores: list[tuple[str, int]] = []
        for mc in (loot.get("magic_cores") or []):
            size = str(mc.get("size", "")).lower()
            if size not in VALID_MC_SIZES:
                raise ValueError(
                    f"ItemBox {box_id!r}: invalid magic-core size {size!r}; "
                    f"expected one of {sorted(VALID_MC_SIZES)}"
                )
            loot_magic_cores.append((f"mc_{size}", int(mc.get("qty", 1))))

        return ItemBox(
            box_id=box_id,
            tile_x=position[0],
            tile_y=position[1],
            loot_items=loot_items,
            loot_magic_cores=loot_magic_cores,
            tile_size=self._tile_size,
            present_requires=present.get("requires", []),
            present_excludes=present.get("excludes", []),
            sprite=self._sprite,
        )
