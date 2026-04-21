# engine/item/magic_core_catalog_state.py

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class MagicCoreCatalogState:
    """Derived magic-core metadata, built from loaded YAML data."""
    ids: set[str] = field(default_factory=set)
    order: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    sizes: list[tuple[str, str, int]] = field(default_factory=list)


def build_mc_catalog(mc_data: list[dict]) -> MagicCoreCatalogState:
    """Build a MagicCoreCatalogState from loaded magic core YAML entries.

    Each entry must have keys: id, name, exchange_rate.
    Entries are expected pre-sorted by exchange_rate descending.
    """
    cat = MagicCoreCatalogState()
    for entry in mc_data:
        mc_id = entry["id"]
        name = entry["name"]
        if "exchange_rate" not in entry:
            raise KeyError(
                f"magic core {mc_id!r}: missing required field 'exchange_rate'"
            )
        rate = entry["exchange_rate"]
        cat.ids.add(mc_id)
        cat.order.append(mc_id)
        cat.labels[mc_id] = name
        cat.sizes.append((mc_id, name, rate))
    return cat
