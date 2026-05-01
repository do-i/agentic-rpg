# tests/unit/core/scenes/test_item_logic.py

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from engine.item.item_entry_state import ItemEntry
from engine.party.repository_state import RepositoryState
from engine.item.item_logic import (
    TABS, item_tab, filtered_items, is_usable,
    actions_for, display_name, discard_item, clamp_scroll,
    EDITABLE_SYSTEM_TAGS, custom_tags, is_system_tag, normalize_custom_tag,
)
from engine.item.magic_core_catalog_state import MagicCoreCatalogState, build_mc_catalog


def make_entry(item_id="potion", qty=5, tags=None, locked=False) -> ItemEntry:
    return ItemEntry(item_id=item_id, qty=qty, tags=tags or set(), locked=locked)


MC_TEST_DATA = [
    {"id": "mc_xl", "name": "Magic Core (XL)", "exchange_rate": 10_000},
    {"id": "mc_l",  "name": "Magic Core (L)",  "exchange_rate": 1_000},
    {"id": "mc_m",  "name": "Magic Core (M)",  "exchange_rate": 100},
    {"id": "mc_s",  "name": "Magic Core (S)",  "exchange_rate": 10},
    {"id": "mc_xs", "name": "Magic Core (XS)", "exchange_rate": 1},
]
TEST_MC_CATALOG = build_mc_catalog(MC_TEST_DATA)


def make_repo_with_items(items: list[tuple[str, int, set]]) -> RepositoryState:
    repo = RepositoryState(gp=1000)
    for item_id, qty, tags in items:
        repo.add_item(item_id, qty)
        entry = repo.get_item(item_id)
        entry.tags = tags
    return repo


# ── item_tab ──────────────────────────────────────────────────

class TestItemTab:
    def test_key_item(self):
        assert item_tab(make_entry(tags={"key"})) == "Key"

    def test_magic_core(self):
        assert item_tab(make_entry(tags={"magic_core"})) == "Magic Core"

    def test_material(self):
        assert item_tab(make_entry(tags={"material"})) == "Material"

    def test_battle(self):
        assert item_tab(make_entry(tags={"battle"})) == "Battle"

    def test_status(self):
        assert item_tab(make_entry(tags={"status"})) == "Status"

    def test_consumable_recovery(self):
        assert item_tab(make_entry(tags={"consumable", "recovery"})) == "Recovery"

    def test_consumable_only(self):
        assert item_tab(make_entry(tags={"consumable"})) == "Recovery"

    def test_fallback_to_all(self):
        assert item_tab(make_entry(tags=set())) == "All"

    def test_battle_consumable_goes_to_battle(self):
        # "battle" without "consumable" -> Battle
        assert item_tab(make_entry(tags={"battle"})) == "Battle"


# ── filtered_items ────────────────────────────────────────────

class TestFilteredItems:
    def test_all_tab_sorted(self):
        repo = make_repo_with_items([
            ("zzz_item", 1, {"consumable"}),
            ("aaa_item", 1, {"consumable"}),
        ])
        result = filtered_items(repo, TABS.index("All"))
        assert [e.id for e in result] == ["aaa_item", "zzz_item"]

    def test_new_tab_filters_to_loot(self):
        repo = make_repo_with_items([
            ("looted", 1, {"consumable"}),
            ("bought", 1, {"consumable"}),
        ])
        repo.get_item("looted").is_loot = True
        result = filtered_items(repo, TABS.index("New"))
        assert [e.id for e in result] == ["looted"]

    def test_recovery_tab_filters(self):
        repo = make_repo_with_items([
            ("potion", 5, {"consumable", "recovery"}),
            ("wolf_fang", 3, {"material"}),
        ])
        result = filtered_items(repo, TABS.index("Recovery"))
        assert len(result) == 1
        assert result[0].id == "potion"

    def test_magic_core_tab_ordered(self):
        repo = make_repo_with_items([
            ("mc_s", 10, {"magic_core"}),
            ("mc_xl", 1, {"magic_core"}),
            ("mc_m", 5, {"magic_core"}),
        ])
        result = filtered_items(repo, TABS.index("Magic Core"), TEST_MC_CATALOG)
        assert [e.id for e in result] == ["mc_xl", "mc_m", "mc_s"]

    def test_material_excludes_magic_core(self):
        repo = make_repo_with_items([
            ("wolf_fang", 3, {"material"}),
            ("mc_s", 10, {"material", "magic_core"}),
        ])
        result = filtered_items(repo, TABS.index("Material"))
        assert len(result) == 1
        assert result[0].id == "wolf_fang"

    def test_key_tab(self):
        repo = make_repo_with_items([
            ("phoenix_wing", 1, {"key"}),
            ("potion", 5, {"consumable"}),
        ])
        result = filtered_items(repo, TABS.index("Key"))
        assert len(result) == 1
        assert result[0].id == "phoenix_wing"

    def test_status_tab(self):
        repo = make_repo_with_items([
            ("antidote", 3, {"consumable", "status"}),
            ("potion", 5, {"consumable", "recovery"}),
        ])
        result = filtered_items(repo, TABS.index("Status"))
        assert len(result) == 1
        assert result[0].id == "antidote"

    def test_battle_tab(self):
        repo = make_repo_with_items([
            ("fire_vial", 2, {"battle"}),
            ("potion", 5, {"consumable", "recovery"}),
        ])
        result = filtered_items(repo, TABS.index("Battle"))
        assert len(result) == 1
        assert result[0].id == "fire_vial"


# ── is_usable ─────────────────────────────────────────────────

class TestIsUsable:
    def test_key_item_not_usable_by_default(self):
        handler = MagicMock()
        entry = make_entry(tags={"key"})
        assert not is_usable(entry, handler)

    def test_key_item_usable_when_flagged(self):
        handler = MagicMock()
        entry = make_entry(tags={"key"})
        entry.usable = True
        assert is_usable(entry, handler)

    def test_material_never_usable(self):
        handler = MagicMock()
        entry = make_entry(tags={"material"})
        assert not is_usable(entry, handler)

    def test_magic_core_never_usable(self):
        handler = MagicMock()
        entry = make_entry(tags={"magic_core"})
        assert not is_usable(entry, handler)

    def test_consumable_delegates_to_handler(self):
        handler = MagicMock()
        handler.is_field_usable.return_value = True
        entry = make_entry(tags={"consumable"})
        assert is_usable(entry, handler)
        handler.is_field_usable.assert_called_with("potion")


# ── actions_for ───────────────────────────────────────────────

class TestActionsFor:
    def test_usable_unlocked_item(self):
        handler = MagicMock()
        handler.is_field_usable.return_value = True
        entry = make_entry(tags={"consumable"}, locked=False)
        assert actions_for(entry, handler) == ["Use", "Discard"]

    def test_locked_item_no_discard(self):
        handler = MagicMock()
        handler.is_field_usable.return_value = True
        entry = make_entry(tags={"consumable"}, locked=True)
        assert actions_for(entry, handler) == ["Use"]

    def test_non_usable_unlocked(self):
        handler = MagicMock()
        handler.is_field_usable.return_value = False
        entry = make_entry(tags={"material"}, locked=False)
        assert actions_for(entry, handler) == ["Discard"]

    def test_non_usable_locked_shows_dash(self):
        handler = MagicMock()
        entry = make_entry(tags={"material"}, locked=True)
        assert actions_for(entry, handler) == ["-"]


# ── display_name ──────────────────────────────────────────────

class TestDisplayName:
    def test_magic_core_uses_label(self):
        entry = make_entry("mc_xl", tags={"magic_core"})
        assert display_name(entry, TEST_MC_CATALOG) == "Magic Core (XL)"

    def test_magic_core_without_catalog_falls_back(self):
        entry = make_entry("mc_xl", tags={"magic_core"})
        assert display_name(entry) == "Mc Xl"

    def test_regular_item_title_cased(self):
        entry = make_entry("hi_potion", tags={"consumable"})
        assert display_name(entry) == "Hi Potion"


# ── discard_item ──────────────────────────────────────────────

class TestDiscardItem:
    def test_removes_item_from_repo(self):
        repo = make_repo_with_items([("potion", 5, {"consumable"})])
        entry = repo.get_item("potion")
        discard_item(repo, entry)
        assert repo.get_item("potion") is None


# ── clamp_scroll ──────────────────────────────────────────────

class TestClampScroll:
    def test_no_change_when_visible(self):
        assert clamp_scroll(3, 0, 14) == 0

    def test_scrolls_up_when_above(self):
        assert clamp_scroll(2, 5, 14) == 2

    def test_scrolls_down_when_below(self):
        assert clamp_scroll(20, 0, 14) == 7  # 20 - 14 + 1

    def test_boundary_exact(self):
        assert clamp_scroll(13, 0, 14) == 0  # still visible at index 13
        assert clamp_scroll(14, 0, 14) == 1  # needs scroll


# ── Tag editor helpers ───────────────────────────────────────

class TestIsSystemTag:
    def test_editable_system_tags_recognized(self):
        for t in EDITABLE_SYSTEM_TAGS:
            assert is_system_tag(t)

    def test_type_driven_tags_recognized(self):
        for t in ("consumable", "material", "key", "magic_core",
                  "equipment", "weapon", "battle", "status", "recovery"):
            assert is_system_tag(t)

    def test_unknown_tag_is_custom(self):
        assert not is_system_tag("my_custom_tag")
        assert not is_system_tag("sell_now")


class TestCustomTags:
    def test_returns_only_non_system(self):
        entry = make_entry(tags={"consumable", "rare", "my_tag", "favorite"})
        # rare and favorite are editable system tags; consumable is type-driven.
        assert custom_tags(entry) == ["my_tag"]

    def test_sorted(self):
        entry = make_entry(tags={"zeta", "alpha", "mu"})
        assert custom_tags(entry) == ["alpha", "mu", "zeta"]


class TestNormalizeCustomTag:
    def test_lowercases(self):
        assert normalize_custom_tag("MyTag") == "mytag"

    def test_strips_whitespace(self):
        assert normalize_custom_tag("  hello  ") == "hello"

    def test_replaces_inner_space_with_underscore(self):
        assert normalize_custom_tag("sell soon") == "sell_soon"

    def test_rejects_empty(self):
        assert normalize_custom_tag("") == ""
        assert normalize_custom_tag("   ") == ""

    def test_rejects_too_long(self):
        assert normalize_custom_tag("x" * 17) == ""

    def test_rejects_disallowed_chars(self):
        assert normalize_custom_tag("hi!") == ""
        assert normalize_custom_tag("foo-bar") == ""

    def test_accepts_alnum_and_underscore(self):
        assert normalize_custom_tag("tag_42") == "tag_42"


# ── build_mc_catalog ─────────────────────────────────────────

class TestBuildMcCatalog:
    def test_builds_ids(self):
        cat = build_mc_catalog(MC_TEST_DATA)
        assert cat.ids == {"mc_xl", "mc_l", "mc_m", "mc_s", "mc_xs"}

    def test_preserves_order(self):
        cat = build_mc_catalog(MC_TEST_DATA)
        assert cat.order == ["mc_xl", "mc_l", "mc_m", "mc_s", "mc_xs"]

    def test_labels(self):
        cat = build_mc_catalog(MC_TEST_DATA)
        assert cat.labels["mc_xl"] == "Magic Core (XL)"
        assert cat.labels["mc_xs"] == "Magic Core (XS)"

    def test_sizes_tuples(self):
        cat = build_mc_catalog(MC_TEST_DATA)
        assert cat.sizes[0] == ("mc_xl", "Magic Core (XL)", 10_000)
        assert cat.sizes[-1] == ("mc_xs", "Magic Core (XS)", 1)

    def test_empty_input(self):
        cat = build_mc_catalog([])
        assert cat.ids == set()
        assert cat.order == []
        assert cat.labels == {}
        assert cat.sizes == []
