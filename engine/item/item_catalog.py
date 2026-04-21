# engine/io/item_catalog.py
#
# Loads all item YAML files from the scenario and provides metadata lookup.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ItemDef:
    """Read-only item definition loaded from scenario YAML."""
    id: str
    name: str
    type: str                          # consumable | material | key | accessory | magic_core
    tags: frozenset[str] = frozenset()
    sell_price: int = 0
    buy_price: int | None = None
    description: str = ""
    sellable: bool = True
    droppable: bool = True


# Map item type -> default system tags applied on add.
_TYPE_TAGS: dict[str, set[str]] = {
    "consumable":  {"consumable"},
    "material":    {"material"},
    "key":         {"key"},
    "accessory":   {"accessory"},
    "magic_core":  {"magic_core"},
}


class ItemCatalog:
    """
    Loads every item YAML file under the scenario items/ directory
    and provides O(1) lookup by item_id.
    """

    def __init__(self, items_dir: Path) -> None:
        self._defs: dict[str, ItemDef] = {}
        self._load(items_dir)

    def _load(self, items_dir: Path) -> None:
        if not items_dir.is_dir():
            return
        for path in sorted(items_dir.glob("*.yaml")):
            # field_use.yaml defines effects, not item metadata — skip
            if path.name == "field_use.yaml":
                continue
            with open(path, "r") as f:
                entries = yaml.safe_load(f) or []
            for entry in entries:
                item_id = entry.get("id")
                if not item_id:
                    continue
                if "name" not in entry:
                    raise KeyError(
                        f"item {item_id!r} ({path.name}): missing required field 'name'"
                    )
                item_type = entry.get("type", "")
                explicit_tags = set(entry.get("tags", []))
                default_tags = _TYPE_TAGS.get(item_type, set())
                all_tags = frozenset(explicit_tags | default_tags)

                self._defs[item_id] = ItemDef(
                    id=item_id,
                    name=entry["name"],
                    type=item_type,
                    tags=all_tags,
                    sell_price=entry.get("sell_price", 0) or 0,
                    buy_price=entry.get("buy_price"),
                    description=entry.get("description", ""),
                    sellable=entry.get("sellable", True),
                    droppable=entry.get("droppable", True),
                )

    def get(self, item_id: str) -> ItemDef | None:
        return self._defs.get(item_id)

    def __contains__(self, item_id: str) -> bool:
        return item_id in self._defs

    def __len__(self) -> int:
        return len(self._defs)

    @property
    def all_ids(self) -> frozenset[str]:
        return frozenset(self._defs.keys())
