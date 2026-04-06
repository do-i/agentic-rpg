# tests/unit/core/encounter/test_encounter_resolver.py

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

from engine.core.encounter.encounter_zone import (
    EncounterZone, EncounterSet, Formation, BossConfig, BarrierEnemy,
    load_encounter_zone,
)
from engine.core.encounter.encounter_resolver import EncounterResolver
from engine.core.encounter.enemy_loader import EnemyLoader
from engine.core.battle.combatant import Combatant
from engine.core.state.flag_state import FlagState


# ── Helpers ───────────────────────────────────────────────────

def make_combatant(name="Wolf") -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=40, hp_max=40, mp=0, mp_max=0,
        atk=10, def_=5, mres=3, dex=10,
        is_enemy=True,
    )


def make_zone(rate=0.15, with_boss=False, with_barrier=False) -> EncounterZone:
    set_a = EncounterSet([
        Formation(["wolf"], 60),
        Formation(["bat", "wolf"], 40),
    ])
    set_b = EncounterSet([
        Formation(["spider"], 100),
    ])
    boss = BossConfig("giant_spider", "Giant Spider", once=True,
                      flag_set="boss_zone01_defeated") if with_boss else None
    barriers = [
        BarrierEnemy("ghost", "veil_breaker", "A force blocks your attack.")
    ] if with_barrier else []
    return EncounterZone(
        zone_id="zone_01", name="Forest", encounter_rate=rate,
        set_a=set_a, set_b=set_b, boss=boss, barrier_enemies=barriers,
    )


def make_loader(*enemy_ids) -> EnemyLoader:
    loader = MagicMock(spec=EnemyLoader)
    loader.load.side_effect = lambda eid: (
        make_combatant(eid) if eid in enemy_ids else None
    )
    return loader


def make_resolver(*enemy_ids) -> EncounterResolver:
    return EncounterResolver(make_loader(*enemy_ids))


# ── load_encounter_zone ───────────────────────────────────────

class TestLoadEncounterZone:
    def test_loads_basic_zone(self, tmp_path):
        data = {
            "id": "zone_01_starting_forest",
            "name": "Starting Forest",
            "encounter_rate": 0.10,
            "set_a": {"entries": [
                {"formation": ["wild_wolf"], "weight": 70},
                {"formation": ["cave_bat"],  "weight": 30},
            ]},
            "set_b": {"entries": [
                {"formation": ["venom_bat"], "weight": 100},
            ]},
        }
        p = tmp_path / "zone_01.yaml"
        p.write_text(yaml.dump(data))
        zone = load_encounter_zone(p)
        assert zone.zone_id == "zone_01_starting_forest"
        assert zone.encounter_rate == 0.10
        assert len(zone.set_a.entries) == 2
        assert len(zone.set_b.entries) == 1

    def test_loads_boss(self, tmp_path):
        data = {
            "id": "zone_01", "name": "Z", "encounter_rate": 0.10,
            "set_a": {"entries": [{"formation": ["wolf"], "weight": 100}]},
            "set_b": {"entries": [{"formation": ["wolf"], "weight": 100}]},
            "boss": {
                "id": "forest_spider_giant",
                "name": "Forest Spider (Giant)",
                "once": True,
                "on_complete": {"set_flag": "boss_zone01_defeated"},
            },
        }
        p = tmp_path / "z.yaml"
        p.write_text(yaml.dump(data))
        zone = load_encounter_zone(p)
        assert zone.boss is not None
        assert zone.boss.enemy_id == "forest_spider_giant"
        assert zone.boss.flag_set == "boss_zone01_defeated"

    def test_loads_barrier_enemies(self, tmp_path):
        data = {
            "id": "zone_04", "name": "Ruins", "encounter_rate": 0.13,
            "set_a": {"entries": [{"formation": ["ghost"], "weight": 100}]},
            "set_b": {"entries": [{"formation": ["skeleton"], "weight": 100}]},
            "barrier_enemies": [
                {"id": "ghost", "requires_item": "veil_breaker",
                 "blocked_message": "A mysterious force blocks your attack."},
            ],
        }
        p = tmp_path / "z.yaml"
        p.write_text(yaml.dump(data))
        zone = load_encounter_zone(p)
        assert len(zone.barrier_enemies) == 1
        assert zone.barrier_enemies[0].requires_item == "veil_breaker"


# ── EncounterResolver.try_random_encounter ────────────────────

class TestTryRandomEncounter:
    def test_no_encounter_when_rate_zero(self):
        zone = make_zone(rate=0.0)
        resolver = make_resolver("wolf", "bat", "spider")
        result = resolver.try_random_encounter(zone, 0.0, FlagState(), set())
        assert result is None

    def test_encounter_fires_when_rate_100(self):
        zone = make_zone(rate=1.0)
        resolver = make_resolver("wolf", "bat", "spider")
        result = resolver.try_random_encounter(zone, 0.0, FlagState(), set())
        assert result is not None

    def test_encounter_has_enemies(self):
        zone = make_zone(rate=1.0)
        resolver = make_resolver("wolf", "bat", "spider")
        result = resolver.try_random_encounter(zone, 0.0, FlagState(), set())
        assert len(result.enemies) >= 1

    def test_modifier_reduces_rate(self):
        zone = make_zone(rate=0.15)
        resolver = make_resolver("wolf")
        with patch("random.randint", return_value=1):
            result = resolver.try_random_encounter(zone, -0.15, FlagState(), set())
            assert result is None   # 0.15 - 0.15 = 0.0 → roll 1 > 0

    def test_barrier_enemy_skipped_without_item(self):
        zone = make_zone(rate=1.0, with_barrier=True)
        # force set_a with ghost formation
        zone.set_a = EncounterSet([Formation(["ghost"], 100)])
        zone.set_b = EncounterSet([Formation(["ghost"], 100)])
        resolver = make_resolver("ghost")
        result = resolver.try_random_encounter(zone, 0.0, FlagState(), set())
        # ghost filtered out — battle should have 0 enemies → None returned
        assert result is None

    def test_barrier_enemy_allowed_with_item(self):
        zone = make_zone(rate=1.0, with_barrier=True)
        zone.set_a = EncounterSet([Formation(["ghost"], 100)])
        zone.set_b = EncounterSet([Formation(["ghost"], 100)])
        resolver = make_resolver("ghost")
        result = resolver.try_random_encounter(
            zone, 0.0, FlagState(), {"veil_breaker"}
        )
        assert result is not None
        assert len(result.enemies) == 1

    def test_barrier_message_surfaced_on_state(self):
        zone = make_zone(rate=1.0, with_barrier=True)
        # formation with ghost (barrier) + wolf (normal)
        zone.set_a = EncounterSet([Formation(["ghost", "wolf"], 100)])
        zone.set_b = EncounterSet([Formation(["ghost", "wolf"], 100)])
        resolver = make_resolver("ghost", "wolf")
        result = resolver.try_random_encounter(zone, 0.0, FlagState(), set())
        # ghost filtered out, but wolf remains
        assert result is not None
        assert len(result.enemies) == 1
        assert result.enemies[0].id == "wolf"
        assert len(result.barrier_messages) == 1
        assert "blocks your attack" in result.barrier_messages[0]

    def test_no_barrier_messages_without_barrier(self):
        zone = make_zone(rate=1.0, with_barrier=False)
        resolver = make_resolver("wolf", "bat", "spider")
        result = resolver.try_random_encounter(zone, 0.0, FlagState(), set())
        assert result is not None
        assert result.barrier_messages == []


# ── EncounterResolver.try_boss_encounter ──────────────────────

class TestTryBossEncounter:
    def test_returns_none_when_no_boss(self):
        zone = make_zone(with_boss=False)
        resolver = make_resolver()
        assert resolver.try_boss_encounter(zone, FlagState()) is None

    def test_returns_state_when_boss_not_defeated(self):
        zone = make_zone(with_boss=True)
        resolver = make_resolver("giant_spider")
        result = resolver.try_boss_encounter(zone, FlagState())
        assert result is not None
        assert result.enemies[0].id == "giant_spider"

    def test_skips_boss_when_flag_set(self):
        zone = make_zone(with_boss=True)
        resolver = make_resolver("giant_spider")
        flags = FlagState({"boss_zone01_defeated"})
        result = resolver.try_boss_encounter(zone, flags)
        assert result is None

    def test_boss_enemy_loaded_correctly(self):
        zone = make_zone(with_boss=True)
        resolver = make_resolver("giant_spider")
        result = resolver.try_boss_encounter(zone, FlagState())
        assert result.enemies[0].name == "giant_spider"


# ── Weighted pick ─────────────────────────────────────────────

class TestWeightedPick:
    def test_always_picks_single_entry(self):
        entries = [Formation(["wolf"], 100)]
        for _ in range(20):
            result = EncounterResolver._weighted_pick(entries)
            assert result.enemy_ids == ["wolf"]

    def test_never_picks_zero_weight(self):
        entries = [
            Formation(["wolf"], 0),
            Formation(["bat"],  100),
        ]
        for _ in range(20):
            result = EncounterResolver._weighted_pick(entries)
            assert result.enemy_ids == ["bat"]

    def test_returns_none_on_empty(self):
        assert EncounterResolver._weighted_pick([]) is None
