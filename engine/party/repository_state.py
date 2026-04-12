# engine/service/repository_state.py
#
# Party Repository — shared item pool + GP.

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.common.item_entry_state import ItemEntry

if TYPE_CHECKING:
    from engine.item.item_catalog import ItemCatalog

# Caps defined in design docs
GP_CAP = 8_000_000
ITEM_QTY_CAP = 100
MAX_TAGS_PER_ITEM = 5


class RepositoryState:
    """
    Party Repository — shared item pool + GP.
    Supports add/remove, sell, tag editing, lock, and tag-based filtering.
    """

    def __init__(self, gp: int = 0, catalog: ItemCatalog | None = None) -> None:
        self._gp: int = gp
        self._items: dict[str, ItemEntry] = {}
        self._catalog: ItemCatalog | None = catalog

    # ── GP ────────────────────────────────────────────────────

    @property
    def gp(self) -> int:
        return self._gp

    def add_gp(self, amount: int) -> None:
        self._gp = min(self._gp + amount, GP_CAP)

    def spend_gp(self, amount: int) -> bool:
        """Returns False if insufficient funds."""
        if self._gp < amount:
            return False
        self._gp -= amount
        return True

    # ── Items — add / get / remove ────────────────────────────

    @property
    def catalog(self) -> ItemCatalog | None:
        return self._catalog

    @catalog.setter
    def catalog(self, catalog: ItemCatalog | None) -> None:
        self._catalog = catalog

    def add_item(self, item_id: str, qty: int = 1) -> ItemEntry:
        """Add qty of item_id. Auto-populates metadata from catalog if set."""
        if item_id in self._items:
            self._items[item_id].qty = min(
                self._items[item_id].qty + qty, ITEM_QTY_CAP
            )
        else:
            entry = ItemEntry(item_id, qty)
            if self._catalog:
                defn = self._catalog.get(item_id)
                if defn:
                    entry.tags = set(defn.tags)
                    entry.name = defn.name
                    entry.description = defn.description
                    entry.sell_price = defn.sell_price
                    entry.sellable = defn.sellable
                    entry.droppable = defn.droppable
            self._items[item_id] = entry
        return self._items[item_id]

    def remove_item(self, item_id: str, qty: int | None = None) -> bool:
        """Remove qty of item (or all if qty is None). Returns False if not found."""
        entry = self._items.get(item_id)
        if not entry:
            return False
        if qty is None or entry.qty <= qty:
            del self._items[item_id]
        else:
            entry.qty -= qty
        return True

    def get_item(self, item_id: str) -> ItemEntry | None:
        return self._items.get(item_id)

    @property
    def items(self) -> list[ItemEntry]:
        return list(self._items.values())

    def has_item(self, item_id: str, qty: int = 1) -> bool:
        entry = self._items.get(item_id)
        return entry is not None and entry.qty >= qty

    # ── Sell ──────────────────────────────────────────────────

    def sell_item(self, item_id: str, qty: int = 1) -> int:
        """Sell qty of an item. Returns GP gained, or 0 if not sellable/missing."""
        entry = self._items.get(item_id)
        if not entry or entry.locked or not entry.sellable:
            return 0
        if entry.qty < qty:
            return 0
        gp_gained = entry.sell_price * qty
        self.remove_item(item_id, qty)
        self.add_gp(gp_gained)
        return gp_gained

    # ── Tags ──────────────────────────────────────────────────

    def add_tag(self, item_id: str, tag: str) -> bool:
        """Add a tag to an item. Respects MAX_TAGS_PER_ITEM. Returns success."""
        entry = self._items.get(item_id)
        if not entry:
            return False
        if tag in entry.tags:
            return True
        if len(entry.tags) >= MAX_TAGS_PER_ITEM:
            return False
        entry.tags.add(tag)
        return True

    def remove_tag(self, item_id: str, tag: str) -> bool:
        """Remove a tag from an item. Returns True if tag was present."""
        entry = self._items.get(item_id)
        if not entry or tag not in entry.tags:
            return False
        entry.tags.discard(tag)
        return True

    # ── Lock ──────────────────────────────────────────────────

    def set_locked(self, item_id: str, locked: bool) -> bool:
        """Set locked flag. Returns False if item not found."""
        entry = self._items.get(item_id)
        if not entry:
            return False
        entry.locked = locked
        return True

    # ── Filtering ─────────────────────────────────────────────

    def items_by_tag(self, tag: str) -> list[ItemEntry]:
        """Return all items that have the given tag."""
        return [e for e in self._items.values() if tag in e.tags]

    def __repr__(self) -> str:
        return f"RepositoryState(gp={self._gp}, items={len(self._items)})"
