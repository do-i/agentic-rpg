# tests/unit/core/state/test_repository_state.py

import pytest
from engine.core.state.repository_state import (
    ItemEntry,
    RepositoryState,
    GP_CAP,
    ITEM_QTY_CAP,
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


# ── Items ─────────────────────────────────────────────────────

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