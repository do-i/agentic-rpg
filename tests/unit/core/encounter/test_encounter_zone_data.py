# tests/unit/core/encounter/test_encounter_zone_data.py
#
# DTO smoke tests — confirm the dataclasses are immutable, accept defaults,
# and that EncounterSet.total_weight sums correctly.

import pytest
from dataclasses import FrozenInstanceError

from engine.encounter.encounter_zone_data import (
    EncounterZone, EncounterSet, Formation, BossConfig, BarrierEnemy,
)


class TestFormation:
    def test_default_chase_range_is_zero(self):
        assert Formation(["wolf"], 50).chase_range == 0

    def test_frozen(self):
        f = Formation(["wolf"], 50)
        with pytest.raises(FrozenInstanceError):
            f.weight = 99


class TestEncounterSet:
    def test_total_weight_sums_entries(self):
        s = EncounterSet([
            Formation(["a"], 10),
            Formation(["b"], 30),
            Formation(["c"], 60),
        ])
        assert s.total_weight == 100

    def test_empty_set_total_weight_zero(self):
        assert EncounterSet().total_weight == 0


class TestBossConfig:
    def test_defaults(self):
        b = BossConfig(enemy_id="dragon", name="Ancient")
        assert b.once is True
        assert b.flag_set == ""

    def test_frozen(self):
        b = BossConfig(enemy_id="x", name="Y")
        with pytest.raises(FrozenInstanceError):
            b.flag_set = "z"


class TestBarrierEnemy:
    def test_default_blocked_message(self):
        b = BarrierEnemy(enemy_id="x", requires_item="key")
        assert b.blocked_message == "A mysterious force blocks your attack."

    def test_frozen(self):
        b = BarrierEnemy(enemy_id="x", requires_item="key")
        with pytest.raises(FrozenInstanceError):
            b.requires_item = "y"


class TestEncounterZone:
    def test_minimum_construction(self):
        z = EncounterZone(zone_id="z", name="Z", density=1.0, entries=EncounterSet())
        assert z.boss is None
        assert z.barrier_enemies == []
        assert z.background == ""
        assert z.spawn_frequency is None

    def test_frozen(self):
        z = EncounterZone(zone_id="z", name="Z", density=1.0, entries=EncounterSet())
        with pytest.raises(FrozenInstanceError):
            z.density = 0.5
