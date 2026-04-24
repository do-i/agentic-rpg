# engine/equipment/equipment_logic.py
#
# Pure-function equipment service.
# - `can_equip` gates an item by class whitelist AND by the member's
#   class `equipment_slots` (slot_category match, or the "all" wildcard).
# - `equip` swaps repository <-> member's slot, returning the displaced item id.
# - `unequip` removes the slot's item back to the repository.
# - `stat_totals` sums base member stats with all equipped numeric stat deltas.
#
# Requires the member's class data already applied via MemberState.load_class_data().

from __future__ import annotations

from engine.party.member_state import MemberState
from engine.party.repository_state import RepositoryState
from engine.item.item_catalog import ItemCatalog, ItemDef, EQUIPMENT_TYPES


BASE_STAT_KEYS = ("str", "dex", "con", "int")


def can_equip(member: MemberState, item: ItemDef) -> bool:
    """True if the member's class can equip the item.

    Two gates, both must pass:
    1. Item's class whitelist (`equippable`) — empty / contains "all" means any class.
    2. Member class's `equipment_slots[item.type]` — must contain "all" or item.slot_category.
    """
    if item.type not in EQUIPMENT_TYPES:
        return False

    if item.equippable and "all" not in item.equippable:
        if member.class_name not in item.equippable:
            return False

    allowed = member.equipment_slots.get(item.type, [])
    if not allowed:
        return False
    if "all" in allowed:
        return True
    return bool(item.slot_category) and item.slot_category in allowed


def equip(
    member: MemberState,
    repo: RepositoryState,
    catalog: ItemCatalog,
    item_id: str,
) -> str | None:
    """Move `item_id` from the repository into the member's slot.

    Returns the previously-equipped item id (or None if the slot was empty).
    The displaced item is returned to the repository.
    Raises ValueError for unknown item, class/slot restriction, or stock shortage.
    """
    item = catalog.get(item_id)
    if item is None:
        raise ValueError(f"Unknown item: {item_id!r}")
    if not can_equip(member, item):
        raise ValueError(
            f"{member.name} ({member.class_name}) cannot equip {item.name} "
            f"[type={item.type}, slot_category={item.slot_category!r}]"
        )
    if not repo.has_item(item_id):
        raise ValueError(f"Item not in repository: {item_id!r}")

    slot = item.type
    prev = member.equipped.get(slot) or None

    repo.remove_item(item_id, 1)
    member.equipped[slot] = item_id
    if prev:
        repo.add_item(prev, 1)
    return prev


def unequip(
    member: MemberState,
    repo: RepositoryState,
    slot: str,
) -> str | None:
    """Remove the slot's equipped item back into the repository.

    Returns the unequipped item id, or None if the slot was empty.
    """
    current = member.equipped.get(slot) or None
    if not current:
        return None
    member.equipped[slot] = ""
    repo.add_item(current)
    return current


def stat_totals(member: MemberState, catalog: ItemCatalog) -> dict[str, int]:
    """Sum of the member's base stats plus all equipped integer stat deltas.

    Non-integer stat entries (e.g. accessory tags like `blocks_ability`) are ignored.
    Unknown numeric stat keys (e.g. "def") are accumulated alongside str/dex/con/int
    so callers can read whatever bonuses equipment defines.
    """
    totals: dict[str, int] = {
        "str": member.str_,
        "dex": member.dex,
        "con": member.con,
        "int": member.int_,
    }
    for item_id in member.equipped.values():
        if not item_id:
            continue
        defn = catalog.get(item_id)
        if defn is None:
            continue
        for stat_name, value in defn.stats:
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            totals[stat_name] = totals.get(stat_name, 0) + value
    return totals


def stat_totals_preview(
    member: MemberState,
    catalog: ItemCatalog,
    slot: str,
    item_id: str | None,
) -> dict[str, int]:
    """Stat totals with `member.equipped[slot]` hypothetically replaced by `item_id`.

    `item_id=None` (or empty) models unequipping the slot. Used to drive the
    `before → after` stat diff shown on the equip picker.
    """
    totals: dict[str, int] = {
        "str": member.str_,
        "dex": member.dex,
        "con": member.con,
        "int": member.int_,
    }
    effective: dict[str, str] = dict(member.equipped)
    effective[slot] = item_id or ""
    for active_id in effective.values():
        if not active_id:
            continue
        defn = catalog.get(active_id)
        if defn is None:
            continue
        for stat_name, value in defn.stats:
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            totals[stat_name] = totals.get(stat_name, 0) + value
    return totals


def equippable_items(
    member: MemberState,
    repo: RepositoryState,
    catalog: ItemCatalog,
    slot: str,
) -> list[ItemDef]:
    """All items in the repository that the member can equip in `slot`."""
    out: list[ItemDef] = []
    for entry in repo.items:
        defn = catalog.get(entry.id)
        if defn is None or defn.type != slot:
            continue
        if can_equip(member, defn):
            out.append(defn)
    return out
