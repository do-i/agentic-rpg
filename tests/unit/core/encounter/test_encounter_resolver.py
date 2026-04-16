# tests/unit/core/encounter/test_encounter_resolver.py

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

from engine.encounter.encounter_zone_data import (
    EncounterZone, EncounterSet, Formation, BossConfig, BarrierEnemy,
)
from engine.encounter.encounter_zone_loader import load_encounter_zone
from engine.encounter.encounter_resolver import EncounterResolver
from engine.battle.enemy_loader import EnemyLoader
from engine.battle.combatant import Combatant
from engine.common.flag_state import FlagState
from engine.util.pseudo_random import PseudoRandom

_rng = PseudoRandom(seed=0)


# ── Helpers ───────────────────────────────────────────────────

def make_combatant(name="Wolf") -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=40, hp_max=40, mp=0, mp_max=0,
        atk=10, def_=5, mres=3, dex=10,
        is_enemy=True,
    )


def make_zone_custom(density=1.0, formation=None, with_barrier=False) -> EncounterZone:
    f = formation or Formation(["wolf"], 100)
    entries = EncounterSet([f])
    barriers = [
        BarrierEnemy("ghost", "veil_breaker", "A force blocks your attack.")
    ] if with_barrier else []
    return EncounterZone(
        zone_id="zone_01", name="Forest", density=density,
        entries=entries, barrier_enemies=barriers,
    )


def make_zone(density=0.15, with_boss=False, with_barrier=False) -> EncounterZone:
    entries = EncounterSet([
        Formation(["wolf"], 60),
        Formation(["bat", "wolf"], 40),
        Formation(["spider"], 100),
    ])
    boss = BossConfig("giant_spider", "Giant Spider", once=True,
                      flag_set="boss_zone01_defeated") if with_boss else None
    barriers = [
        BarrierEnemy("ghost", "veil_breaker", "A force blocks your attack.")
    ] if with_barrier else []
    return EncounterZone(
        zone_id="zone_01", name="Forest", density=density,
        entries=entries, boss=boss, barrier_enemies=barriers,
    )


def make_loader(*enemy_ids) -> EnemyLoader:
    loader = MagicMock(spec=EnemyLoader)
    loader.load.side_effect = lambda eid: (
        make_combatant(eid) if eid in enemy_ids else None
    )
    return loader


def make_resolver(*enemy_ids) -> EncounterResolver:
    return EncounterResolver(make_loader(*enemy_ids), _rng)


# ── load_encounter_zone ───────────────────────────────────────

class TestLoadEncounterZone:
    def test_loads_basic_zone(self, tmp_path):
        data = {
            "id": "zone_01_starting_forest",
            "name": "Starting Forest",
            "density": 0.70,
            "entries": [
                {"formation": ["wild_wolf"], "weight": 70},
                {"formation": ["cave_bat"],  "weight": 30},
                {"formation": ["venom_bat"], "weight": 100},
            ],
        }
        p = tmp_path / "zone_01.yaml"
        p.write_text(yaml.dump(data))
        zone = load_encounter_zone(p)
        assert zone.zone_id == "zone_01_starting_forest"
        assert zone.density == 0.70
        assert len(zone.entries.entries) == 3

    def test_loads_spawn_frequency(self, tmp_path):
        data = {
            "id": "zone_01", "name": "Z", "density": 0.5,
            "spawn_frequency": 15.0,
            "entries": [{"formation": ["wolf"], "weight": 100}],
        }
        p = tmp_path / "z.yaml"
        p.write_text(yaml.dump(data))
        zone = load_encounter_zone(p)
        assert zone.spawn_frequency == 15.0

    def test_loads_chase_range_per_formation(self, tmp_path):
        data = {
            "id": "zone_01", "name": "Z", "density": 0.5,
            "entries": [
                {"formation": ["wolf"], "weight": 100, "chase_range": 4},
                {"formation": ["bat"], "weight": 50},
            ],
        }
        p = tmp_path / "z.yaml"
        p.write_text(yaml.dump(data))
        zone = load_encounter_zone(p)
        assert zone.entries.entries[0].chase_range == 4
        assert zone.entries.entries[1].chase_range == 0  # default

    def test_loads_boss(self, tmp_path):
        data = {
            "id": "zone_01", "name": "Z", "density": 0.10,
            "entries": [{"formation": ["wolf"], "weight": 100}],
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
            "id": "zone_04", "name": "Ruins", "density": 0.13,
            "entries": [{"formation": ["ghost"], "weight": 100}],
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


# ── EncounterResolver.build_battle_from_formation ─────────────

class TestBuildBattleFromFormation:
    def test_builds_state_with_enemies(self):
        zone = make_zone(density=1.0)
        resolver = make_resolver("wolf", "bat")
        formation = Formation(["wolf", "bat"], 100)
        state = resolver.build_battle_from_formation(formation, zone, set())
        assert state is not None
        assert len(state.enemies) == 2

    def test_returns_none_when_all_enemies_barrier_blocked(self):
        zone = make_zone_custom(formation=Formation(["ghost"], 100), with_barrier=True)
        resolver = make_resolver("ghost")
        formation = Formation(["ghost"], 100)
        result = resolver.build_battle_from_formation(formation, zone, set())
        assert result is None

    def test_barrier_enemy_allowed_with_item(self):
        zone = make_zone_custom(formation=Formation(["ghost"], 100), with_barrier=True)
        resolver = make_resolver("ghost")
        formation = Formation(["ghost"], 100)
        result = resolver.build_battle_from_formation(formation, zone, {"veil_breaker"})
        assert result is not None
        assert len(result.enemies) == 1

    def test_barrier_message_surfaced(self):
        zone = make_zone_custom(formation=Formation(["ghost", "wolf"], 100), with_barrier=True)
        resolver = make_resolver("ghost", "wolf")
        formation = Formation(["ghost", "wolf"], 100)
        result = resolver.build_battle_from_formation(formation, zone, set())
        assert result is not None
        assert len(result.enemies) == 1
        assert result.enemies[0].id == "wolf"
        assert len(result.barrier_messages) == 1

    def test_background_from_zone(self):
        zone = EncounterZone(
            zone_id="z", name="Z", density=1.0,
            entries=EncounterSet([Formation(["wolf"], 100)]),
            background="world1-bg",
        )
        resolver = make_resolver("wolf")
        state = resolver.build_battle_from_formation(Formation(["wolf"], 100), zone, set())
        assert state.background == "world1-bg"


# ── EncounterResolver.build_battle_from_boss ──────────────────

class TestBuildBattleFromBoss:
    def test_returns_none_when_no_boss(self):
        zone = make_zone(with_boss=False)
        resolver = make_resolver()
        assert resolver.build_battle_from_boss(zone, FlagState()) is None

    def test_returns_state_when_boss_not_defeated(self):
        zone = make_zone(with_boss=True)
        resolver = make_resolver("giant_spider")
        result = resolver.build_battle_from_boss(zone, FlagState())
        assert result is not None
        assert result.enemies[0].id == "giant_spider"

    def test_skips_boss_when_flag_set(self):
        zone = make_zone(with_boss=True)
        resolver = make_resolver("giant_spider")
        flags = FlagState({"boss_zone01_defeated"})
        result = resolver.build_battle_from_boss(zone, flags)
        assert result is None

    def test_boss_flag_on_state(self):
        zone = make_zone(with_boss=True)
        resolver = make_resolver("giant_spider")
        result = resolver.build_battle_from_boss(zone, FlagState())
        assert result.boss_flag == "boss_zone01_defeated"


# ── EncounterResolver.pick_formation ─────────────────────────

class TestPickFormation:
    def test_returns_formation_from_zone(self):
        zone = make_zone()
        resolver = make_resolver("wolf")
        result = resolver.pick_formation(zone)
        assert result is not None
        assert len(result.enemy_ids) >= 1

    def test_returns_none_for_empty_entries(self):
        zone = EncounterZone(
            zone_id="z", name="Z", density=1.0,
            entries=EncounterSet([]),
        )
        resolver = make_resolver()
        assert resolver.pick_formation(zone) is None


# ── Weighted pick ─────────────────────────────────────────────

class TestWeightedPick:
    def _resolver(self):
        return make_resolver()

    def test_always_picks_single_entry(self):
        resolver = self._resolver()
        entries = [Formation(["wolf"], 100)]
        for _ in range(20):
            result = resolver._weighted_pick(entries)
            assert result.enemy_ids == ["wolf"]

    def test_never_picks_zero_weight(self):
        resolver = self._resolver()
        entries = [
            Formation(["wolf"], 0),
            Formation(["bat"],  100),
        ]
        for _ in range(20):
            result = resolver._weighted_pick(entries)
            assert result.enemy_ids == ["bat"]

    def test_returns_none_on_empty(self):
        assert self._resolver()._weighted_pick([]) is None
