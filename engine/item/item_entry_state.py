# engine/dto/item_entry.py


from __future__ import annotations

class ItemEntry:
    """Single item stack in the Party Repository."""

    def __init__(
        self,
        item_id: str,
        qty: int = 1,
        tags: set[str] | None = None,
        locked: bool = False,
        name: str = "",
        description: str = "",
        sell_price: int = 0,
        sellable: bool = True,
        droppable: bool = True,
    ) -> None:
        self.id = item_id
        self.qty = qty
        self.tags: set[str] = tags if tags is not None else set()
        self.locked = locked
        self.name = name or item_id.replace("_", " ").title()
        self.description = description
        self.sell_price = sell_price
        self.sellable = sellable
        self.droppable = droppable
        self.is_loot = False

    def __repr__(self) -> str:
        return f"ItemEntry({self.id!r}, qty={self.qty}, locked={self.locked})"
