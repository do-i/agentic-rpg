# tests/unit/core/item/test_item_catalog.py

from __future__ import annotations

import pytest
from pathlib import Path
from engine.item.item_catalog import ItemCatalog, ItemDef


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

    def test_loads_equipment(self):
        items_dir = Path("rusted_kingdoms/data/items")
        if not items_dir.is_dir():
            pytest.skip("Scenario data not available")
        cat = ItemCatalog(items_dir)
        iron = cat.get("iron_sword")
        assert iron is not None
        assert iron.type == "weapon"
        assert iron.slot_category == "sword"
        assert ("str", 4) in iron.stats
        assert "equipment" in iron.tags
        assert "weapon" in iron.tags


@pytest.fixture
def equipment_dir(tmp_path):
    d = tmp_path / "items"
    d.mkdir()
    (d / "weapons.yaml").write_text(
        "- id: iron_sword\n"
        "  name: Iron Sword\n"
        "  type: weapon\n"
        "  slot_category: sword\n"
        "  stats:\n"
        "    str: 4\n"
        "  buy_price: 350\n"
        "  sell_price: 175\n"
        "  description: basic blade\n"
        "- id: heroes_blade\n"
        "  name: Heroes Blade\n"
        "  type: weapon\n"
        "  slot_category: sword\n"
        "  equippable: [hero]\n"
        "  stats:\n"
        "    str: 8\n"
        "    dex: 2\n"
        "  buy_price: null\n"
        "  sell_price: null\n"
        "  description: quest reward\n"
    )
    return d


class TestEquipmentLoading:
    def test_loads_slot_category(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        assert cat.get("iron_sword").slot_category == "sword"

    def test_loads_stats_tuple(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        stats = dict(cat.get("iron_sword").stats)
        assert stats == {"str": 4}

    def test_loads_negative_stat_deltas(self, equipment_dir):
        d = equipment_dir
        (d / "axes.yaml").write_text(
            "- id: axe\n"
            "  name: Axe\n"
            "  type: weapon\n"
            "  slot_category: axe\n"
            "  stats:\n"
            "    str: 5\n"
            "    dex: -1\n"
            "  buy_price: 400\n"
            "  sell_price: 200\n"
        )
        cat = ItemCatalog(d)
        stats = dict(cat.get("axe").stats)
        assert stats["dex"] == -1

    def test_equippable_whitelist(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        assert cat.get("heroes_blade").equippable == frozenset({"hero"})

    def test_empty_equippable_for_unrestricted(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        assert cat.get("iron_sword").equippable == frozenset()

    def test_null_sell_price_marks_unsellable(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        assert cat.get("heroes_blade").sellable is False
        assert cat.get("heroes_blade").sell_price == 0

    def test_null_buy_price_is_none(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        assert cat.get("heroes_blade").buy_price is None

    def test_missing_buy_price_raises(self, tmp_path):
        d = tmp_path / "items"
        d.mkdir()
        (d / "weapons.yaml").write_text(
            "- id: no_buy\n"
            "  name: No Buy\n"
            "  type: weapon\n"
            "  slot_category: sword\n"
            "  sell_price: 100\n"
        )
        with pytest.raises(ValueError, match="buy_price"):
            ItemCatalog(d)

    def test_missing_sell_price_raises(self, tmp_path):
        d = tmp_path / "items"
        d.mkdir()
        (d / "weapons.yaml").write_text(
            "- id: no_sell\n"
            "  name: No Sell\n"
            "  type: weapon\n"
            "  slot_category: sword\n"
            "  buy_price: 100\n"
        )
        with pytest.raises(ValueError, match="sell_price"):
            ItemCatalog(d)

    def test_missing_slot_category_on_weapon_raises(self, tmp_path):
        d = tmp_path / "items"
        d.mkdir()
        (d / "weapons.yaml").write_text(
            "- id: no_slot\n"
            "  name: No Slot\n"
            "  type: weapon\n"
            "  buy_price: 100\n"
            "  sell_price: 50\n"
        )
        with pytest.raises(ValueError, match="slot_category"):
            ItemCatalog(d)

    def test_accessory_may_omit_slot_category(self, tmp_path):
        d = tmp_path / "items"
        d.mkdir()
        (d / "accessories.yaml").write_text(
            "- id: charm\n"
            "  name: Charm\n"
            "  type: accessory\n"
            "  equippable: [all]\n"
            "  buy_price: 100\n"
            "  sell_price: 50\n"
        )
        cat = ItemCatalog(d)   # must not raise
        assert cat.get("charm").slot_category == ""

    def test_equipment_gets_equipment_and_type_tags(self, equipment_dir):
        cat = ItemCatalog(equipment_dir)
        tags = cat.get("iron_sword").tags
        assert "equipment" in tags
        assert "weapon" in tags

    def test_stats_preserves_non_numeric_values(self, tmp_path):
        d = tmp_path / "items"
        d.mkdir()
        (d / "accessories.yaml").write_text(
            "- id: talisman\n"
            "  name: Talisman\n"
            "  type: accessory\n"
            "  stats:\n"
            "    blocks_ability: death_gaze\n"
            "  buy_price: null\n"
            "  sell_price: 0\n"
        )
        cat = ItemCatalog(d)
        stats = dict(cat.get("talisman").stats)
        assert stats["blocks_ability"] == "death_gaze"
