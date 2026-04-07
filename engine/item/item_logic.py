# engine/item/item_logic.py
#
# Item scene logic — filtering, usability checks, use/discard actions.
# Extracted from item_scene.py to separate data logic from rendering.

from __future__ import annotations

from dataclasses import dataclass, field

from engine.state.repository_state import ItemEntry, RepositoryState
from engine.item.item_effect_handler import ItemEffectHandler

# ── Tabs — Magic Core inserted between Material and Key ───────
TABS = ["New", "All", "Recovery", "Status", "Battle", "Material", "Magic Core", "Key"]


# ── Magic Core catalog — built from scenario data ─────────────

@dataclass
class MCCatalog:
    """Derived magic-core metadata, built from loaded YAML data."""
    ids: set[str] = field(default_factory=set)
    order: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    sizes: list[tuple[str, str, int]] = field(default_factory=list)


def build_mc_catalog(mc_data: list[dict]) -> MCCatalog:
    """Build an MCCatalog from loaded magic core YAML entries.

    Each entry should have keys: id, name, exchange_rate.
    Entries are expected pre-sorted by exchange_rate descending.
    """
    cat = MCCatalog()
    for entry in mc_data:
        mc_id = entry["id"]
        name = entry["name"]
        rate = entry.get("exchange_rate", 0)
        cat.ids.add(mc_id)
        cat.order.append(mc_id)
        cat.labels[mc_id] = name
        cat.sizes.append((mc_id, name, rate))
    return cat


def item_tab(entry: ItemEntry) -> str:
    """Determine which tab an item belongs to."""
    tags = entry.tags
    if "key" in tags:
        return "Key"
    if "magic_core" in tags:
        return "Magic Core"
    if "material" in tags:
        return "Material"
    if "battle" in tags and "consumable" not in tags:
        return "Battle"
    if "status" in tags:
        return "Status"
    if "consumable" in tags or "recovery" in tags:
        return "Recovery"
    return "All"


def filtered_items(repo: RepositoryState, tab_index: int,
                   mc_catalog: MCCatalog | None = None) -> list[ItemEntry]:
    """Return items matching the given tab index."""
    all_items = repo.items
    tab = TABS[tab_index]

    if tab == "New":
        return list(reversed(all_items))
    if tab == "All":
        return sorted(all_items, key=lambda e: e.id)
    if tab == "Magic Core":
        mc_order = mc_catalog.order if mc_catalog else []
        owned = {e.id: e for e in all_items if "magic_core" in e.tags}
        return [owned[mc_id] for mc_id in mc_order if mc_id in owned]

    def matches(e: ItemEntry) -> bool:
        tags = e.tags
        if tab == "Recovery":
            return ("recovery" in tags or
                    ("consumable" in tags
                     and "status" not in tags
                     and "battle" not in tags
                     and "key" not in tags
                     and "material" not in tags
                     and "magic_core" not in tags))
        if tab == "Status":
            return "status" in tags
        if tab == "Battle":
            return "battle" in tags
        if tab == "Material":
            return "material" in tags and "magic_core" not in tags
        if tab == "Key":
            return "key" in tags
        return True

    return sorted(filter(matches, all_items), key=lambda e: e.id)


def is_usable(entry: ItemEntry, effect_handler: ItemEffectHandler) -> bool:
    """True if item can be used in field context."""
    if "key" in entry.tags:
        return getattr(entry, "usable", False)
    if "material" in entry.tags or "magic_core" in entry.tags:
        return False
    return effect_handler.is_field_usable(entry.id)


def actions_for(entry: ItemEntry, effect_handler: ItemEffectHandler) -> list[str]:
    """Return available actions for the given item."""
    actions = []
    if is_usable(entry, effect_handler):
        actions.append("Use")
    if not entry.locked:
        actions.append("Discard")
    return actions or ["—"]


def display_name(entry: ItemEntry, mc_catalog: MCCatalog | None = None) -> str:
    """Human-readable name for an item entry."""
    if "magic_core" in entry.tags and mc_catalog and entry.id in mc_catalog.labels:
        return mc_catalog.labels[entry.id]
    return entry.name or entry.id.replace("_", " ").title()


def discard_item(repo: RepositoryState, entry: ItemEntry) -> None:
    """Remove an item entirely from the repository."""
    repo.remove_item(entry.id)


def clamp_scroll(list_sel: int, scroll: int, visible_rows: int) -> int:
    """Return adjusted scroll position to keep list_sel visible."""
    if list_sel < scroll:
        return list_sel
    if list_sel >= scroll + visible_rows:
        return list_sel - visible_rows + 1
    return scroll
