# tests/unit/core/item/test_item_catalog.py

import pytest
from pathlib import Path
from engine.io.item_catalog import ItemCatalog, ItemDef


@pytest.fixture
def items_dir(tmp_path):
    """Create a temp items directory with test YAML files."""
    d = tmp_path / "items"
    d.mkdir()

    (d / "consumables.yaml").write_text(
        "- id: potion\n"
        "  name: Potion\n"
        "  type: consumable\n"
        "  sell_price: 50\n"
        "  buy_price: 100\n"
        "  description: Restores 100 HP.\n"
        "- id: elixir\n"
        "  name: Elixir\n"
        "  type: consumable\n"
        "  sell_price: 0\n"
        "  description: Fully restores HP and MP.\n"
    )
    (d / "materials.yaml").write_text(
        "- id: wolf_fang\n"
        "  name: Wolf Fang\n"
        "  type: material\n"
        "  sell_price: 20\n"
    )
    (d / "key_items.yaml").write_text(
        "- id: phoenix_wing\n"
        "  name: Phoenix Wing\n"
        "  type: key\n"
        "  sellable: false\n"
        "  droppable: false\n"
        "  description: Revives a fallen ally.\n"
    )
    (d / "magic_cores.yaml").write_text(
        "- id: mc_s\n"
        "  name: 'Magic Core (S)'\n"
        "  type: magic_core\n"
        "  tags: [magic_core]\n"
        "  exchange_rate: 10\n"
    )
    # field_use.yaml should be skipped
    (d / "field_use.yaml").write_text(
        "- id: potion\n"
        "  effect: restore_hp\n"
        "  amount: 100\n"
        "  target: single_alive\n"
    )
    return d


class TestItemCatalogLoad:
    def test_loads_all_items(self, items_dir):
        cat = ItemCatalog(items_dir)
        assert len(cat) == 5

    def test_skips_field_use(self, items_dir):
        cat = ItemCatalog(items_dir)
        # potion exists from consumables, not duplicated from field_use
        assert cat.get("potion") is not None

    def test_missing_dir_loads_empty(self, tmp_path):
        cat = ItemCatalog(tmp_path / "nonexistent")
        assert len(cat) == 0


class TestItemCatalogGet:
    def test_get_existing(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("potion")
        assert defn is not None
        assert defn.name == "Potion"
        assert defn.type == "consumable"
        assert defn.sell_price == 50
        assert defn.buy_price == 100
        assert defn.description == "Restores 100 HP."

    def test_get_missing(self, items_dir):
        cat = ItemCatalog(items_dir)
        assert cat.get("nonexistent") is None

    def test_contains(self, items_dir):
        cat = ItemCatalog(items_dir)
        assert "potion" in cat
        assert "nonexistent" not in cat

    def test_all_ids(self, items_dir):
        cat = ItemCatalog(items_dir)
        assert cat.all_ids == frozenset({"potion", "elixir", "wolf_fang", "phoenix_wing", "mc_s"})


class TestItemCatalogTags:
    def test_consumable_gets_consumable_tag(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("potion")
        assert "consumable" in defn.tags

    def test_material_gets_material_tag(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("wolf_fang")
        assert "material" in defn.tags

    def test_key_gets_key_tag(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("phoenix_wing")
        assert "key" in defn.tags

    def test_magic_core_explicit_tags_merged(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("mc_s")
        assert "magic_core" in defn.tags


class TestItemCatalogProperties:
    def test_key_item_not_sellable(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("phoenix_wing")
        assert defn.sellable is False
        assert defn.droppable is False

    def test_default_sellable(self, items_dir):
        cat = ItemCatalog(items_dir)
        defn = cat.get("potion")
        assert defn.sellable is True
        assert defn.droppable is True


class TestItemCatalogRealData:
    """Smoke test against actual scenario data."""

    def test_loads_rusted_kingdoms(self):
        items_dir = Path("rusted_kingdoms/data/items")
        if not items_dir.is_dir():
            pytest.skip("Scenario data not available")
        cat = ItemCatalog(items_dir)
        assert len(cat) > 10
        assert "potion" in cat
        assert "wolf_fang" in cat
        assert "mc_s" in cat
        assert "phoenix_wing" in cat
