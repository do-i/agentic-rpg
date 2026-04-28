# tests/unit/core/state/test_item_entry_state.py

from engine.item.item_entry_state import ItemEntry


class TestConstruction:
    def test_minimum_construction(self):
        e = ItemEntry("potion")
        assert e.id == "potion"
        assert e.qty == 1
        assert e.tags == set()
        assert e.locked is False
        # Default name title-cases the id.
        assert e.name == "Potion"
        assert e.description == ""
        assert e.sell_price == 0
        assert e.sellable is True
        assert e.droppable is True

    def test_explicit_name_overrides_default(self):
        e = ItemEntry("hi_potion", name="High Potion")
        assert e.name == "High Potion"

    def test_default_name_handles_underscores(self):
        e = ItemEntry("phoenix_down")
        assert e.name == "Phoenix Down"

    def test_tags_default_is_independent_set(self):
        a = ItemEntry("a")
        b = ItemEntry("b")
        a.tags.add("starter")
        assert "starter" not in b.tags  # not shared default

    def test_explicit_tags(self):
        e = ItemEntry("key_card", tags={"key", "quest"})
        assert e.tags == {"key", "quest"}

    def test_qty_carried(self):
        e = ItemEntry("bomb", qty=3)
        assert e.qty == 3

    def test_locked_carried(self):
        e = ItemEntry("plot_item", locked=True)
        assert e.locked is True

    def test_repr_has_id_qty_locked(self):
        e = ItemEntry("potion", qty=5, locked=True)
        r = repr(e)
        assert "potion" in r
        assert "5" in r
        assert "True" in r
