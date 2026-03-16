# engine/core/state/repository_state.py
#
# STUB — full implementation in Phase 6 (shop / apothecary)
# For now: holds gp and a flat item list.

# Caps defined in design docs
GP_CAP = 8_000_000
ITEM_QTY_CAP = 100


class ItemEntry:
    """Stub — single item stack in the Party Repository."""

    def __init__(
        self,
        item_id: str,
        qty: int = 1,
        tags: list[str] | None = None,
        locked: bool = False,
    ) -> None:
        self.id = item_id
        self.qty = qty
        self.tags: list[str] = tags if tags is not None else []
        self.locked = locked

    def __repr__(self) -> str:
        return f"ItemEntry({self.id!r}, qty={self.qty}, locked={self.locked})"


class RepositoryState:
    """
    Stub — Party Repository (shared item pool + GP).
    Full logic (tag editing, sell, filter) added in Phase 6.
    """

    def __init__(self, gp: int = 0) -> None:
        self._gp: int = gp
        self._items: list[ItemEntry] = []

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

    # ── Items ─────────────────────────────────────────────────

    def add_item(self, item_id: str, qty: int = 1) -> None:
        for entry in self._items:
            if entry.id == item_id:
                entry.qty = min(entry.qty + qty, ITEM_QTY_CAP)
                return
        self._items.append(ItemEntry(item_id, qty))

    def get_item(self, item_id: str) -> ItemEntry | None:
        for entry in self._items:
            if entry.id == item_id:
                return entry
        return None

    @property
    def items(self) -> list[ItemEntry]:
        return list(self._items)

    def __repr__(self) -> str:
        return f"RepositoryState(gp={self._gp}, items={len(self._items)})"
