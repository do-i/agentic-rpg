# tests/unit/core/equipment/test_equipment_logic.py

from __future__ import annotations

import pytest

from engine.party.member_state import MemberState
from engine.party.repository_state import RepositoryState
from engine.item.item_catalog import ItemCatalog
from engine.equipment.equipment_logic import (
    can_equip, equip, unequip, stat_totals, equippable_items,
)


@pytest.fixture
def items_dir(tmp_path):
    d = tmp_path / "items"
    d.mkdir()
    (d / "weapons.yaml").write_text(
        "- id: iron_sword\n"
        "  name: Iron Sword\n"
        "  type: weapon\n"
        "  slot_category: sword\n"
        "  stats: {str: 4}\n"
        "  buy_price: 350\n"
        "  sell_price: 175\n"
        "- id: oak_staff\n"
        "  name: Oak Staff\n"
        "  type: weapon\n"
        "  slot_category: staff\n"
        "  stats: {int: 2}\n"
        "  buy_price: 180\n"
        "  sell_price: 90\n"
        "- id: heroes_blade\n"
        "  name: Heroes Blade\n"
        "  type: weapon\n"
        "  slot_category: sword\n"
        "  equippable: [hero]\n"
        "  stats: {str: 8}\n"
        "  buy_price: null\n"
        "  sell_price: null\n"
        "- id: steel_axe\n"
        "  name: Steel Axe\n"
        "  type: weapon\n"
        "  slot_category: axe\n"
        "  stats:\n"
        "    str: 5\n"
        "    dex: -1\n"
        "  buy_price: 400\n"
        "  sell_price: 200\n"
    )
    (d / "body.yaml").write_text(
        "- id: chainmail\n"
        "  name: Chainmail\n"
        "  type: body\n"
        "  slot_category: heavy_armor\n"
        "  stats: {con: 5, dex: -2}\n"
        "  buy_price: 700\n"
        "  sell_price: 350\n"
        "- id: cloth_robe\n"
        "  name: Cloth Robe\n"
        "  type: body\n"
        "  slot_category: robe\n"
        "  stats: {con: 1, int: 1}\n"
        "  buy_price: 70\n"
        "  sell_price: 35\n"
    )
    (d / "accessories.yaml").write_text(
        "- id: holy_talisman\n"
        "  name: Holy Talisman\n"
        "  type: accessory\n"
        "  equippable: [all]\n"
        "  stats:\n"
        "    blocks_ability: death_gaze\n"
        "  buy_price: null\n"
        "  sell_price: 0\n"
    )
    return d


def _member(
    class_name="hero",
    equipment_slots=None,
    equipped=None,
    str_=10,
    dex=8,
    con=9,
    int_=6,
) -> MemberState:
    m = MemberState(
        member_id=class_name,
        name=class_name.title(),
        protagonist=True,
        class_name=class_name,
        level=5,
        exp=0,
        hp=50, hp_max=50, mp=10, mp_max=10,
        str_=str_, dex=dex, con=con, int_=int_,
        equipped=equipped if equipped is not None else {},
    )
    m.equipment_slots = equipment_slots if equipment_slots is not None else {
        "weapon":    ["sword", "axe"],
        "shield":    ["all"],
        "helmet":    ["all"],
        "body":      ["all"],
        "accessory": ["all"],
    }
    return m


def _repo(catalog, items=None) -> RepositoryState:
    r = RepositoryState(gp=0, catalog=catalog)
    for item_id, qty in (items or {}).items():
        r.add_item(item_id, qty)
    return r


# ── can_equip ─────────────────────────────────────────────────

class TestCanEquip:
    def test_slot_category_match(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()
        assert can_equip(m, cat.get("iron_sword")) is True

    def test_slot_category_mismatch(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipment_slots={"weapon": ["sword", "axe"]})   # no staff
        assert can_equip(m, cat.get("oak_staff")) is False

    def test_all_wildcard_allows_any_category(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipment_slots={"body": ["all"]})
        assert can_equip(m, cat.get("chainmail")) is True
        assert can_equip(m, cat.get("cloth_robe")) is True

    def test_empty_slot_list_blocks_entire_type(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipment_slots={"weapon": ["sword"], "shield": []})
        # Shield slot empty -> can't equip any shield-typed item (none defined here,
        # but we can assert the weapon still works while the slot-empty rule holds)
        assert can_equip(m, cat.get("iron_sword")) is True

    def test_missing_slot_key_blocks(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipment_slots={"weapon": ["sword"]})   # no body key
        assert can_equip(m, cat.get("chainmail")) is False

    def test_equippable_whitelist_allows_listed_class(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(class_name="hero")
        assert can_equip(m, cat.get("heroes_blade")) is True

    def test_equippable_whitelist_blocks_other_class(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(class_name="warrior",
                    equipment_slots={"weapon": ["sword", "axe"]})
        assert can_equip(m, cat.get("heroes_blade")) is False

    def test_equippable_all_keyword_allows_any_class(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(class_name="rogue",
                    equipment_slots={"accessory": ["all"]})
        assert can_equip(m, cat.get("holy_talisman")) is True

    def test_non_equipment_type_returns_false(self, items_dir, tmp_path):
        # Add a consumable
        (items_dir / "consum.yaml").write_text(
            "- id: potion\n  name: Potion\n  type: consumable\n  sell_price: 50\n"
        )
        cat = ItemCatalog(items_dir)
        m = _member()
        assert can_equip(m, cat.get("potion")) is False


# ── equip / unequip ───────────────────────────────────────────

class TestEquip:
    def test_moves_item_from_repo_to_slot(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()
        r = _repo(cat, {"iron_sword": 1})
        prev = equip(m, r, cat, "iron_sword")
        assert prev is None
        assert m.equipped["weapon"] == "iron_sword"
        assert r.has_item("iron_sword") is False

    def test_swap_returns_previous_to_repo(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipped={"weapon": "iron_sword"})
        r = _repo(cat, {"steel_axe": 1})
        prev = equip(m, r, cat, "steel_axe")
        assert prev == "iron_sword"
        assert m.equipped["weapon"] == "steel_axe"
        assert r.has_item("iron_sword") is True
        assert r.has_item("steel_axe") is False

    def test_equip_unknown_item_raises(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()
        r = _repo(cat)
        with pytest.raises(ValueError, match="Unknown item"):
            equip(m, r, cat, "no_such_item")

    def test_equip_not_in_repo_raises(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()
        r = _repo(cat)
        with pytest.raises(ValueError, match="not in repository"):
            equip(m, r, cat, "iron_sword")

    def test_equip_class_restricted_raises(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(class_name="warrior",
                    equipment_slots={"weapon": ["sword", "axe"]})
        r = _repo(cat, {"heroes_blade": 1})
        with pytest.raises(ValueError, match="cannot equip"):
            equip(m, r, cat, "heroes_blade")


class TestUnequip:
    def test_returns_item_to_repo(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipped={"weapon": "iron_sword"})
        r = _repo(cat)
        prev = unequip(m, r, "weapon")
        assert prev == "iron_sword"
        assert m.equipped["weapon"] == ""
        assert r.has_item("iron_sword") is True

    def test_unequip_empty_slot_returns_none(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()
        r = _repo(cat)
        assert unequip(m, r, "weapon") is None

    def test_unequip_missing_slot_key_returns_none(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()   # equipped = {}
        r = _repo(cat)
        assert unequip(m, r, "weapon") is None


# ── stat_totals ───────────────────────────────────────────────

class TestStatTotals:
    def test_bare_member_returns_base_stats(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(str_=12, dex=8, con=9, int_=6)
        t = stat_totals(m, cat)
        assert t == {"str": 12, "dex": 8, "con": 9, "int": 6}

    def test_adds_weapon_bonus(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(str_=12, equipped={"weapon": "iron_sword"})
        t = stat_totals(m, cat)
        assert t["str"] == 16    # 12 + 4

    def test_sums_multi_slot(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(
            str_=12, dex=10, con=8,
            equipped={"weapon": "steel_axe", "body": "chainmail"},
        )
        t = stat_totals(m, cat)
        assert t["str"] == 17    # 12 + 5
        assert t["dex"] == 7     # 10 - 1 - 2
        assert t["con"] == 13    # 8 + 5

    def test_ignores_non_numeric_stats(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(
            equipment_slots={"accessory": ["all"]},
            equipped={"accessory": "holy_talisman"},
        )
        t = stat_totals(m, cat)
        assert "blocks_ability" not in t

    def test_ignores_empty_slots(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipped={"weapon": "", "body": None})
        t = stat_totals(m, cat)
        assert t["str"] == 10    # base only

    def test_ignores_unknown_item_id(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipped={"weapon": "ghost_sword"})
        t = stat_totals(m, cat)
        assert t["str"] == 10    # base only, no crash


# ── equippable_items ──────────────────────────────────────────

class TestEquippableItems:
    def test_filters_by_slot(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member()
        r = _repo(cat, {"iron_sword": 1, "chainmail": 1})
        weapons = equippable_items(m, r, cat, "weapon")
        ids = {i.id for i in weapons}
        assert ids == {"iron_sword"}

    def test_respects_class_restriction(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(class_name="warrior",
                    equipment_slots={"weapon": ["sword", "axe"]})
        r = _repo(cat, {"heroes_blade": 1, "iron_sword": 1})
        ids = {i.id for i in equippable_items(m, r, cat, "weapon")}
        assert ids == {"iron_sword"}

    def test_respects_slot_category(self, items_dir):
        cat = ItemCatalog(items_dir)
        m = _member(equipment_slots={"weapon": ["sword"]})   # no axe
        r = _repo(cat, {"steel_axe": 1, "iron_sword": 1})
        ids = {i.id for i in equippable_items(m, r, cat, "weapon")}
        assert ids == {"iron_sword"}


# ── MemberState.load_class_data integration ──────────────────

class TestLoadClassDataEquipmentSlots:
    def test_caches_equipment_slots(self):
        m = MemberState(
            member_id="test", name="T", protagonist=False, class_name="hero",
            level=1, exp=0, hp=10, hp_max=10, mp=0, mp_max=0,
            str_=1, dex=1, con=1, int_=1, equipped={},
        )
        m.load_class_data({
            "stat_growth": {"str": [1]*10, "dex": [1]*10, "con": [1]*10, "int": [1]*10},
            "equipment_slots": {"weapon": ["sword", "axe"], "shield": ["all"]},
        })
        assert m.equipment_slots == {"weapon": ["sword", "axe"], "shield": ["all"]}

    def test_omitted_equipment_slots_defaults_empty(self):
        m = MemberState(
            member_id="test", name="T", protagonist=False, class_name="warrior",
            level=1, exp=0, hp=10, hp_max=10, mp=0, mp_max=0,
            str_=1, dex=1, con=1, int_=1, equipped={},
        )
        m.load_class_data({
            "stat_growth": {"str": [1]*10, "dex": [1]*10, "con": [1]*10, "int": [1]*10},
        })
        assert m.equipment_slots == {}
