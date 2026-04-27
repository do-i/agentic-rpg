# engine/io/item_catalog.py
#
# Loads all item YAML files from the scenario and provides metadata lookup.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from engine.io.yaml_loader import load_yaml_required


EQUIPMENT_TYPES: frozenset[str] = frozenset({
    "weapon", "shield", "helmet", "body", "accessory",
})


@dataclass(frozen=True)
class ItemDef:
    """Read-only item definition loaded from scenario YAML."""
    id: str
    name: str
    type: str                          # consumable | material | key | magic_core | weapon | shield | helmet | body | accessory
    tags: frozenset[str] = frozenset()
    sell_price: int = 0
    buy_price: int | None = None
    description: str = ""
    sellable: bool = True
    droppable: bool = True
    # Equipment-only fields. Defaults leave consumables unaffected.
    slot_category: str = ""                          # "" = unspecified (accessories usually use class `equippable`)
    equippable: frozenset[str] = frozenset()         # empty = no class whitelist (subject to class equipment_slots)
    stats: tuple[tuple[str, object], ...] = ()       # ordered stat entries, e.g. (("str", 3), ("dex", -1), ("encounter_modifier", -0.15))


# Map item type -> default system tags applied on add.
_TYPE_TAGS: dict[str, set[str]] = {
    "consumable":  {"consumable"},
    "material":    {"material"},
    "key":         {"key"},
    "accessory":   {"accessory"},
    "magic_core":  {"magic_core"},
    "weapon":      {"equipment", "weapon"},
    "shield":      {"equipment", "shield"},
    "helmet":      {"equipment", "helmet"},
    "body":        {"equipment", "body"},
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
            entries = load_yaml_required(path) or []
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

                if item_type in EQUIPMENT_TYPES:
                    self._require_price_keys(entry, path.name, item_id)
                    if item_type == "accessory":
                        # accessories may omit slot_category — class-side `accessory: [all]` gates them.
                        slot_category = entry.get("slot_category") or ""
                    else:
                        slot_category = self._require_slot_category(entry, path.name, item_id)
                    equippable = frozenset(entry.get("equippable") or [])
                    stats = self._parse_stats(entry.get("stats"), path.name, item_id)
                    sell_price_raw = entry.get("sell_price")
                    sell_price = int(sell_price_raw) if sell_price_raw is not None else 0
                    sellable = entry.get("sellable", sell_price_raw is not None)
                else:
                    slot_category = ""
                    equippable = frozenset()
                    stats = ()
                    sell_price = entry.get("sell_price", 0) or 0
                    sellable = entry.get("sellable", True)

                self._defs[item_id] = ItemDef(
                    id=item_id,
                    name=entry["name"],
                    type=item_type,
                    tags=all_tags,
                    sell_price=sell_price,
                    buy_price=entry.get("buy_price"),
                    description=entry.get("description", ""),
                    sellable=sellable,
                    droppable=entry.get("droppable", True),
                    slot_category=slot_category,
                    equippable=equippable,
                    stats=stats,
                )

    @staticmethod
    def _require_price_keys(entry: dict, filename: str, item_id: str) -> None:
        for key in ("buy_price", "sell_price"):
            if key not in entry:
                raise ValueError(
                    f"item {item_id!r} ({filename}): equipment requires explicit "
                    f"{key!r}. Use null to mark unsellable. "
                    f"Example:\n  {key}: 100   # or {key}: null"
                )

    @staticmethod
    def _require_slot_category(entry: dict, filename: str, item_id: str) -> str:
        val = entry.get("slot_category")
        if not val:
            raise ValueError(
                f"item {item_id!r} ({filename}): equipment type "
                f"{entry.get('type')!r} requires 'slot_category'. "
                f"Example:\n  slot_category: sword"
            )
        return str(val)

    @staticmethod
    def _parse_stats(raw, filename: str, item_id: str) -> tuple[tuple[str, object], ...]:
        if raw is None:
            return ()
        if not isinstance(raw, dict):
            raise ValueError(
                f"item {item_id!r} ({filename}): 'stats' must be a mapping. "
                f"Example:\n  stats:\n    str: 3\n    dex: -1"
            )
        return tuple((str(k), v) for k, v in raw.items())

    def get(self, item_id: str) -> ItemDef | None:
        return self._defs.get(item_id)

    def __contains__(self, item_id: str) -> bool:
        return item_id in self._defs

    def __len__(self) -> int:
        return len(self._defs)

    @property
    def all_ids(self) -> frozenset[str]:
        return frozenset(self._defs.keys())
