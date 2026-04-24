# tests/unit/core/encounter/test_encounter_manager.py

import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock

from engine.encounter.encounter_manager import EncounterManager
from engine.party.member_state import MemberState
from engine.party.party_state import PartyState
from engine.party.repository_state import RepositoryState


ZONE_YAML = """\
id: zone_01
name: Starting Forest
density: 0.8
entries:
  - formation: [goblin]
    weight: 60
    chase_range: 3
  - formation: [bat]
    weight: 40
    chase_range: 2
"""

CLASS_YAML = """\
stat_growth:
  hp: [10]
  mp: [5]
  str: [2]
  dex: [2]
  con: [2]
  int: [2]
abilities:
  - id: slash
    unlock_level: 1
  - id: power_strike
    unlock_level: 3
"""


@pytest.fixture
def encount_dir(tmp_path):
    d = tmp_path / "encount"
    d.mkdir()
    (d / "zone_01.yaml").write_text(ZONE_YAML)
    return d


@pytest.fixture
def classes_dir(tmp_path):
    d = tmp_path / "classes"
    d.mkdir()
    (d / "hero.yaml").write_text(CLASS_YAML)
    return d


@pytest.fixture
def manager(encount_dir, classes_dir):
    return EncounterManager(encount_dir=encount_dir, classes_dir=classes_dir)


def make_member(class_name="hero", level=2):
    return MemberState(
        member_id="aric", name="Aric", protagonist=True,
        class_name=class_name, level=level, exp=0, exp_next=100,
        hp=50, hp_max=50, mp=20, mp_max=20,
        str_=10, dex=8, con=9, int_=6, equipped={},
    )


# ── set_zone / get_zone ───────────────────────────────────────

class TestSetZone:
    def test_loads_zone_when_file_exists(self, manager):
        manager.set_zone("zone_01")
        zone = manager.get_zone()
        assert zone is not None
        assert zone.zone_id == "zone_01"

    def test_zone_is_none_for_missing_file(self, manager):
        manager.set_zone("nonexistent_map")
        assert manager.get_zone() is None

    def test_same_zone_id_returns_early(self, manager):
        manager.set_zone("zone_01")
        zone_first = manager.get_zone()
        manager.set_zone("zone_01")
        assert manager.get_zone() is zone_first  # same object, no reload

    def test_caches_zone_across_different_set_calls(self, manager):
        manager.set_zone("zone_01")
        z1 = manager.get_zone()
        manager.set_zone("nonexistent_map")
        manager.set_zone("zone_01")
        z2 = manager.get_zone()
        assert z1 is z2  # loaded from cache, same instance


# ── add_mc_drops ──────────────────────────────────────────────

class TestAddMcDrops:
    def test_adds_items_with_magic_core_tag(self):
        repo = RepositoryState()
        EncounterManager.add_mc_drops(repo, [{"size": "S", "qty": 2}])
        assert len(repo.items) == 1
        assert repo.items[0].id == "mc_s"
        assert repo.items[0].qty == 2
        assert "magic_core" in repo.items[0].tags

    def test_multiple_drops(self):
        repo = RepositoryState()
        EncounterManager.add_mc_drops(repo, [
            {"size": "S", "qty": 1},
            {"size": "L", "qty": 3},
        ])
        ids = {e.id for e in repo.items}
        assert "mc_s" in ids
        assert "mc_l" in ids

    def test_empty_drops_no_change(self):
        repo = RepositoryState()
        EncounterManager.add_mc_drops(repo, [])
        assert len(repo.items) == 0


# ── fill_party ────────────────────────────────────────────────

class TestFillParty:
    def test_fill_party_sets_party_on_battle_state(self, manager):
        member = make_member()
        party = MagicMock()
        party.members = [member]
        battle_state = MagicMock()

        manager.fill_party(battle_state, party)

        assert len(battle_state.party) == 1
        battle_state.build_turn_order.assert_called_once()

    def test_member_converted_to_combatant(self, manager):
        member = make_member(level=2)
        party = MagicMock()
        party.members = [member]
        battle_state = MagicMock()

        manager.fill_party(battle_state, party)

        combatant = battle_state.party[0]
        assert combatant.name == "Aric"
        assert not combatant.is_enemy

    def test_combatant_stats_use_base_when_no_catalog(self, manager):
        member = make_member()   # str_=10 dex=8 con=9 int_=6
        party = MagicMock()
        party.members = [member]
        battle_state = MagicMock()
        manager.fill_party(battle_state, party)
        c = battle_state.party[0]
        assert c.atk == 10 and c.dex == 8 and c.def_ == 9 and c.mres == 6

    def test_combatant_stats_include_equipment_bonuses(self, encount_dir, classes_dir, tmp_path):
        from engine.item.item_catalog import ItemCatalog
        items_dir = tmp_path / "items"
        items_dir.mkdir()
        (items_dir / "weapons.yaml").write_text(
            "- id: iron_sword\n"
            "  name: Iron Sword\n"
            "  type: weapon\n"
            "  slot_category: sword\n"
            "  stats: {str: 4, dex: -1}\n"
            "  buy_price: 350\n"
            "  sell_price: 175\n"
        )
        catalog = ItemCatalog(items_dir)
        mgr = EncounterManager(
            encount_dir=encount_dir, classes_dir=classes_dir, item_catalog=catalog,
        )
        member = make_member()       # str=10 dex=8 con=9 int=6
        member.equipment_slots = {"weapon": ["sword"]}
        member.equipped = {"weapon": "iron_sword"}

        party = MagicMock(); party.members = [member]
        battle_state = MagicMock()
        mgr.fill_party(battle_state, party)
        c = battle_state.party[0]
        assert c.atk == 14      # 10 + 4
        assert c.dex == 7       # 8 - 1
        assert c.def_ == 9      # unchanged
        assert c.mres == 6      # unchanged


# ── _load_class_abilities ─────────────────────────────────────

class TestLoadClassAbilities:
    def test_returns_empty_when_no_classes_dir(self, encount_dir):
        mgr = EncounterManager(encount_dir=encount_dir)
        abilities = mgr._load_class_abilities("hero", level=5)
        assert abilities == []

    def test_returns_empty_when_class_file_missing(self, manager):
        abilities = manager._load_class_abilities("unknown_class", level=5)
        assert abilities == []

    def test_filters_by_unlock_level(self, manager):
        # level=2: only unlock_level<=2 → only "slash" (unlock_level=1)
        abilities = manager._load_class_abilities("hero", level=2)
        ids = [a["id"] for a in abilities]
        assert "slash" in ids
        assert "power_strike" not in ids

    def test_includes_all_unlocked_at_higher_level(self, manager):
        abilities = manager._load_class_abilities("hero", level=5)
        ids = [a["id"] for a in abilities]
        assert "slash" in ids
        assert "power_strike" in ids

    def test_caches_class_data(self, manager):
        first = manager._load_class_abilities("hero", level=5)
        # Second call hits cache (same object in cache)
        second = manager._load_class_abilities("hero", level=5)
        assert first == second
        assert "hero" in manager._class_cache
