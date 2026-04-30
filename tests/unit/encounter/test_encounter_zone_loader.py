# tests/unit/core/encounter/test_encounter_zone_loader.py

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from engine.encounter.encounter_zone_loader import load_encounter_zone
from engine.encounter.encounter_zone_data import (
    EncounterZone, EncounterSet, Formation, BossConfig, BarrierEnemy,
)


def write_zone(tmp_path: Path, data: dict, name: str = "zone_01.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.dump(data))
    return p


# ── Required fields ──────────────────────────────────────────

class TestRequiredFields:
    def test_missing_density_raises(self, tmp_path):
        p = write_zone(tmp_path, {"id": "z", "entries": []})
        with pytest.raises(KeyError, match="density"):
            load_encounter_zone(p)

    def test_entry_missing_chase_range_raises(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0,
            "entries": [{"formation": ["wolf"], "weight": 50}],
        })
        with pytest.raises(KeyError, match="chase_range"):
            load_encounter_zone(p)


# ── Entry parsing ────────────────────────────────────────────

class TestEntryParsing:
    def test_basic_zone_round_trip(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "starting_forest",
            "name": "Starting Forest",
            "density": 0.8,
            "entries": [
                {"formation": ["wolf"], "weight": 50, "chase_range": 100},
                {"formation": ["bat", "bat"], "weight": 25, "chase_range": 80},
            ],
        })
        zone = load_encounter_zone(p)
        assert isinstance(zone, EncounterZone)
        assert zone.zone_id == "starting_forest"
        assert zone.name == "Starting Forest"
        assert zone.density == 0.8
        assert len(zone.entries.entries) == 2
        first = zone.entries.entries[0]
        assert first.enemy_ids == ["wolf"]
        assert first.weight == 50
        assert first.chase_range == 100

    def test_no_entries_yields_empty_set(self, tmp_path):
        p = write_zone(tmp_path, {"id": "z", "name": "Z", "density": 1.0})
        zone = load_encounter_zone(p)
        assert isinstance(zone.entries, EncounterSet)
        assert zone.entries.entries == []

    def test_zone_id_falls_back_to_file_stem(self, tmp_path):
        p = write_zone(tmp_path, {"density": 1.0, "name": "Z"}, name="cave_03.yaml")
        zone = load_encounter_zone(p)
        assert zone.zone_id == "cave_03"


# ── Boss parsing ─────────────────────────────────────────────

class TestBossParsing:
    def test_no_boss_yields_none(self, tmp_path):
        p = write_zone(tmp_path, {"id": "z", "density": 1.0})
        assert load_encounter_zone(p).boss is None

    def test_full_boss_config(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0,
            "boss": {
                "id": "dragon", "name": "Ancient Dragon", "once": True,
                "on_complete": {"set_flag": "boss_defeated"},
            },
        })
        boss = load_encounter_zone(p).boss
        assert isinstance(boss, BossConfig)
        assert boss.enemy_id == "dragon"
        assert boss.name == "Ancient Dragon"
        assert boss.once is True
        assert boss.flag_set == "boss_defeated"

    def test_boss_name_defaults_to_id(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0,
            "boss": {"id": "lich"},
        })
        boss = load_encounter_zone(p).boss
        assert boss.name == "lich"

    def test_boss_once_defaults_true(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0, "boss": {"id": "lich"},
        })
        boss = load_encounter_zone(p).boss
        assert boss.once is True

    def test_boss_without_on_complete_has_empty_flag_set(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0,
            "boss": {"id": "lich"},
        })
        boss = load_encounter_zone(p).boss
        assert boss.flag_set == ""


# ── Barrier parsing ──────────────────────────────────────────

class TestBarrierParsing:
    def test_barrier_round_trip(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0,
            "barrier_enemies": [{
                "id": "veil_guard",
                "requires_item": "veil_breaker",
                "blocked_message": "The veil resists.",
            }],
        })
        barriers = load_encounter_zone(p).barrier_enemies
        assert len(barriers) == 1
        assert isinstance(barriers[0], BarrierEnemy)
        assert barriers[0].enemy_id == "veil_guard"
        assert barriers[0].requires_item == "veil_breaker"
        assert barriers[0].blocked_message == "The veil resists."

    def test_barrier_missing_blocked_message_raises(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0,
            "barrier_enemies": [{"id": "v", "requires_item": "x"}],
        })
        with pytest.raises(KeyError, match="blocked_message"):
            load_encounter_zone(p)


# ── Optional metadata ────────────────────────────────────────

class TestOptionalFields:
    def test_background_round_trip(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0, "background": "bg/forest.png",
        })
        assert load_encounter_zone(p).background == "bg/forest.png"

    def test_spawn_frequency_round_trip(self, tmp_path):
        p = write_zone(tmp_path, {
            "id": "z", "density": 1.0, "spawn_frequency": 12.5,
        })
        assert load_encounter_zone(p).spawn_frequency == 12.5

    def test_spawn_frequency_omitted_is_none(self, tmp_path):
        p = write_zone(tmp_path, {"id": "z", "density": 1.0})
        assert load_encounter_zone(p).spawn_frequency is None
