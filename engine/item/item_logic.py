# engine/item/item_logic.py
#
# Item scene logic — filtering, usability checks, use/discard actions.
# Extracted from item_scene.py to separate data logic from rendering.

from __future__ import annotations

from engine.item.item_entry_state import ItemEntry
from engine.party.repository_state import RepositoryState
from engine.item.item_effect_handler import ItemEffectHandler
from engine.item.magic_core_catalog_state import MagicCoreCatalogState, build_mc_catalog

# ── Tabs — Magic Core inserted between Material and Key ───────
TABS = ["All", "New", "Recovery", "Status", "Battle", "Material", "Magic Core", "Key"]

# ── Tag editor ────────────────────────────────────────────────
# Curatorial system tags exposed in the Edit Tags UI. Tags driven by item
# type (consumable, material, key, magic_core, equipment, weapon, …) are
# excluded — toggling them would silently re-categorize the item under a
# different tab.
EDITABLE_SYSTEM_TAGS: tuple[str, ...] = ("rare", "sell_soon", "favorite")

CUSTOM_TAG_MAX_LEN = 16
_CUSTOM_TAG_ALLOWED = set("abcdefghijklmnopqrstuvwxyz0123456789_")


def custom_tags(entry: ItemEntry) -> list[str]:
    """Tags on the entry that are neither editable system tags nor
    type-driven system tags. Sorted for stable display."""
    return sorted(t for t in entry.tags if not is_system_tag(t))


def is_system_tag(tag: str) -> bool:
    """True for any tag the engine treats as system-managed.
    System tags include the editable curatorial set plus type-driven tags
    (consumable/material/key/magic_core/equipment/...) that come from the
    item catalog."""
    if tag in EDITABLE_SYSTEM_TAGS:
        return True
    return tag in {
        "consumable", "material", "key", "magic_core",
        "equipment", "weapon", "shield", "helmet", "body", "accessory",
        "battle", "status", "recovery",
    }


def normalize_custom_tag(raw: str) -> str:
    """Lowercase, trim, validate. Returns empty string if invalid."""
    s = raw.strip().lower().replace(" ", "_")
    if not s or len(s) > CUSTOM_TAG_MAX_LEN:
        return ""
    if any(ch not in _CUSTOM_TAG_ALLOWED for ch in s):
        return ""
    return s


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
                   mc_catalog: MagicCoreCatalogState | None = None) -> list[ItemEntry]:
    """Return items matching the given tab index."""
    all_items = repo.items
    tab = TABS[tab_index]

    if tab == "New":
        return sorted((e for e in all_items if e.is_loot), key=lambda e: e.id)
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
    return actions or ["-"]


def display_name(entry: ItemEntry, mc_catalog: MagicCoreCatalogState | None = None) -> str:
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
