# tests/unit/core/state/test_repository_state.py

import pytest
from engine.common.item_entry_state import ItemEntry
from engine.party.repository_state import (
    RepositoryState,
    GP_CAP,
    ITEM_QTY_CAP,
    MAX_TAGS_PER_ITEM,
)


# ── ItemEntry ─────────────────────────────────────────────────

class TestItemEntry:
    def test_defaults(self):
        e = ItemEntry("potion")
        assert e.id == "potion"
        assert e.qty == 1
        assert e.tags == set()
        assert e.locked is False

    def test_tags_are_set(self):
        e = ItemEntry("potion", tags={"consumable", "battle"})
        assert isinstance(e.tags, set)

    def test_locked_flag(self):
        e = ItemEntry("elixir", locked=True)
        assert e.locked is True

    def test_name_defaults_to_title_case(self):
        e = ItemEntry("hi_potion")
        assert e.name == "Hi Potion"

    def test_name_explicit(self):
        e = ItemEntry("potion", name="Potion")
        assert e.name == "Potion"

    def test_description_defaults_empty(self):
        e = ItemEntry("potion")
        assert e.description == ""

    def test_description_explicit(self):
        e = ItemEntry("potion", description="Heals 100 HP.")
        assert e.description == "Heals 100 HP."

    def test_sell_price_defaults_to_zero(self):
        e = ItemEntry("potion")
        assert e.sell_price == 0

    def test_sellable_default(self):
        e = ItemEntry("potion")
        assert e.sellable is True
        assert e.droppable is True


# ── GP ────────────────────────────────────────────────────────

class TestGP:
    def test_default_gp_is_zero(self):
        r = RepositoryState()
        assert r.gp == 0

    def test_add_gp(self):
        r = RepositoryState()
        r.add_gp(500)
        assert r.gp == 500

    def test_add_gp_accumulates(self):
        r = RepositoryState()
        r.add_gp(500)
        r.add_gp(300)
        assert r.gp == 800

    def test_add_gp_capped_at_max(self):
        r = RepositoryState()
        r.add_gp(GP_CAP + 1_000_000)
        assert r.gp == GP_CAP

    def test_add_gp_exact_cap(self):
        r = RepositoryState()
        r.add_gp(GP_CAP)
        assert r.gp == GP_CAP

    def test_spend_gp_returns_true_on_success(self):
        r = RepositoryState(gp=1000)
        assert r.spend_gp(500) is True

    def test_spend_gp_deducts_amount(self):
        r = RepositoryState(gp=1000)
        r.spend_gp(300)
        assert r.gp == 700

    def test_spend_gp_returns_false_insufficient(self):
        r = RepositoryState(gp=100)
        assert r.spend_gp(500) is False

    def test_spend_gp_does_not_deduct_on_failure(self):
        r = RepositoryState(gp=100)
        r.spend_gp(500)
        assert r.gp == 100

    def test_spend_exact_balance(self):
        r = RepositoryState(gp=500)
        assert r.spend_gp(500) is True
        assert r.gp == 0


# ── Items — add / get ─────────────────────────────────────────

class TestItems:
    def test_add_new_item(self):
        r = RepositoryState()
        r.add_item("potion")
        assert r.get_item("potion") is not None

    def test_add_item_default_qty(self):
        r = RepositoryState()
        r.add_item("potion")
        assert r.get_item("potion").qty == 1

    def test_add_item_with_qty(self):
        r = RepositoryState()
        r.add_item("potion", qty=5)
        assert r.get_item("potion").qty == 5

    def test_add_item_accumulates_qty(self):
        r = RepositoryState()
        r.add_item("potion", qty=3)
        r.add_item("potion", qty=4)
        assert r.get_item("potion").qty == 7

    def test_add_item_qty_capped(self):
        r = RepositoryState()
        r.add_item("potion", qty=ITEM_QTY_CAP)
        r.add_item("potion", qty=10)
        assert r.get_item("potion").qty == ITEM_QTY_CAP

    def test_get_item_returns_none_for_missing(self):
        r = RepositoryState()
        assert r.get_item("elixir") is None

    def test_multiple_different_items(self):
        r = RepositoryState()
        r.add_item("potion", qty=3)
        r.add_item("elixir", qty=1)
        assert r.get_item("potion").qty == 3
        assert r.get_item("elixir").qty == 1

    def test_items_property_returns_all(self):
        r = RepositoryState()
        r.add_item("potion")
        r.add_item("elixir")
        ids = {e.id for e in r.items}
        assert ids == {"potion", "elixir"}

    def test_items_property_returns_copy(self):
        r = RepositoryState()
        r.add_item("potion")
        items = r.items
        items.clear()
        assert r.get_item("potion") is not None

    def test_add_item_returns_entry(self):
        r = RepositoryState()
        entry = r.add_item("potion", 3)
        assert entry.id == "potion"
        assert entry.qty == 3

    def test_has_item_true(self):
        r = RepositoryState()
        r.add_item("potion", 5)
        assert r.has_item("potion", 3) is True

    def test_has_item_exact(self):
        r = RepositoryState()
        r.add_item("potion", 5)
        assert r.has_item("potion", 5) is True

    def test_has_item_insufficient(self):
        r = RepositoryState()
        r.add_item("potion", 2)
        assert r.has_item("potion", 5) is False

    def test_has_item_missing(self):
        r = RepositoryState()
        assert r.has_item("potion") is False


# ── Remove ────────────────────────────────────────────────────

class TestRemoveItem:
    def test_remove_all(self):
        r = RepositoryState()
        r.add_item("potion", 5)
        assert r.remove_item("potion") is True
        assert r.get_item("potion") is None

    def test_remove_partial(self):
        r = RepositoryState()
        r.add_item("potion", 5)
        assert r.remove_item("potion", 3) is True
        assert r.get_item("potion").qty == 2

    def test_remove_exact_qty(self):
        r = RepositoryState()
        r.add_item("potion", 3)
        r.remove_item("potion", 3)
        assert r.get_item("potion") is None

    def test_remove_more_than_owned(self):
        r = RepositoryState()
        r.add_item("potion", 2)
        r.remove_item("potion", 5)
        assert r.get_item("potion") is None

    def test_remove_missing_item(self):
        r = RepositoryState()
        assert r.remove_item("nonexistent") is False

    def test_remove_one_decrements(self):
        r = RepositoryState()
        r.add_item("potion", 5)
        r.remove_item("potion", 1)
        assert r.get_item("potion").qty == 4


# ── Sell ──────────────────────────────────────────────────────

class TestSellItem:
    def test_sell_adds_gp(self):
        r = RepositoryState(gp=100)
        r.add_item("potion", 5)
        entry = r.get_item("potion")
        entry.sell_price = 50
        gp = r.sell_item("potion", 2)
        assert gp == 100
        assert r.gp == 200

    def test_sell_removes_qty(self):
        r = RepositoryState()
        r.add_item("potion", 5)
        r.get_item("potion").sell_price = 50
        r.sell_item("potion", 3)
        assert r.get_item("potion").qty == 2

    def test_sell_all_removes_entry(self):
        r = RepositoryState()
        r.add_item("potion", 3)
        r.get_item("potion").sell_price = 50
        r.sell_item("potion", 3)
        assert r.get_item("potion") is None

    def test_sell_locked_returns_zero(self):
        r = RepositoryState()
        r.add_item("elixir", 1)
        entry = r.get_item("elixir")
        entry.sell_price = 100
        entry.locked = True
        assert r.sell_item("elixir", 1) == 0
        assert r.get_item("elixir").qty == 1

    def test_sell_not_sellable_returns_zero(self):
        r = RepositoryState()
        r.add_item("key_item", 1)
        entry = r.get_item("key_item")
        entry.sell_price = 100
        entry.sellable = False
        assert r.sell_item("key_item", 1) == 0

    def test_sell_insufficient_qty_returns_zero(self):
        r = RepositoryState()
        r.add_item("potion", 2)
        r.get_item("potion").sell_price = 50
        assert r.sell_item("potion", 5) == 0
        assert r.get_item("potion").qty == 2

    def test_sell_missing_returns_zero(self):
        r = RepositoryState()
        assert r.sell_item("nonexistent", 1) == 0


# ── Tags ──────────────────────────────────────────────────────

class TestTags:
    def test_add_tag(self):
        r = RepositoryState()
        r.add_item("potion")
        assert r.add_tag("potion", "battle") is True
        assert "battle" in r.get_item("potion").tags

    def test_add_tag_duplicate(self):
        r = RepositoryState()
        r.add_item("potion")
        r.add_tag("potion", "battle")
        assert r.add_tag("potion", "battle") is True

    def test_add_tag_at_limit(self):
        r = RepositoryState()
        r.add_item("potion")
        for i in range(MAX_TAGS_PER_ITEM):
            r.add_tag("potion", f"tag{i}")
        assert r.add_tag("potion", "one_more") is False
        assert len(r.get_item("potion").tags) == MAX_TAGS_PER_ITEM

    def test_add_tag_missing_item(self):
        r = RepositoryState()
        assert r.add_tag("nonexistent", "battle") is False

    def test_remove_tag(self):
        r = RepositoryState()
        r.add_item("potion")
        r.add_tag("potion", "battle")
        assert r.remove_tag("potion", "battle") is True
        assert "battle" not in r.get_item("potion").tags

    def test_remove_tag_not_present(self):
        r = RepositoryState()
        r.add_item("potion")
        assert r.remove_tag("potion", "battle") is False

    def test_remove_tag_missing_item(self):
        r = RepositoryState()
        assert r.remove_tag("nonexistent", "battle") is False


# ── Lock ──────────────────────────────────────────────────────

class TestLock:
    def test_set_locked(self):
        r = RepositoryState()
        r.add_item("elixir")
        assert r.set_locked("elixir", True) is True
        assert r.get_item("elixir").locked is True

    def test_unlock(self):
        r = RepositoryState()
        r.add_item("elixir")
        r.set_locked("elixir", True)
        r.set_locked("elixir", False)
        assert r.get_item("elixir").locked is False

    def test_set_locked_missing(self):
        r = RepositoryState()
        assert r.set_locked("nonexistent", True) is False


# ── Filtering ─────────────────────────────────────────────────

class TestItemsByTag:
    def test_filter_by_tag(self):
        r = RepositoryState()
        r.add_item("potion")
        r.get_item("potion").tags = {"consumable", "recovery"}
        r.add_item("wolf_fang")
        r.get_item("wolf_fang").tags = {"material"}
        r.add_item("elixir")
        r.get_item("elixir").tags = {"consumable", "recovery"}

        results = r.items_by_tag("consumable")
        ids = {e.id for e in results}
        assert ids == {"potion", "elixir"}

    def test_filter_empty_result(self):
        r = RepositoryState()
        r.add_item("potion")
        assert r.items_by_tag("nonexistent") == []


# ── Catalog integration ───────────────────────────────────────

class TestCatalogIntegration:
    def _make_catalog(self, tmp_path):
        d = tmp_path / "items"
        d.mkdir()
        (d / "consumables.yaml").write_text(
            "- id: potion\n"
            "  name: Potion\n"
            "  type: consumable\n"
            "  sell_price: 50\n"
            "  description: Restores 100 HP.\n"
        )
        from engine.item.item_catalog import ItemCatalog
        return ItemCatalog(d)

    def test_add_item_auto_populates_from_catalog(self, tmp_path):
        cat = self._make_catalog(tmp_path)
        r = RepositoryState(catalog=cat)
        r.add_item("potion", 3)
        entry = r.get_item("potion")
        assert entry.name == "Potion"
        assert entry.description == "Restores 100 HP."
        assert entry.sell_price == 50
        assert "consumable" in entry.tags

    def test_add_item_unknown_to_catalog(self, tmp_path):
        cat = self._make_catalog(tmp_path)
        r = RepositoryState(catalog=cat)
        r.add_item("mystery_item", 1)
        entry = r.get_item("mystery_item")
        assert entry.name == "Mystery Item"
        assert entry.tags == set()

    def test_add_item_without_catalog(self):
        r = RepositoryState()
        r.add_item("potion", 1)
        entry = r.get_item("potion")
        assert entry.name == "Potion"
        assert entry.tags == set()
