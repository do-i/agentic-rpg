# tests/unit/core/state/test_game_state_manager.py

import pytest
from pathlib import Path
from unittest.mock import patch

import yaml

from engine.common.io.save_manager import GameStateManager
from engine.common.io.game_state_loader import from_new_game

MANIFEST_STUB = {
    "protagonist": {
        "id": "aric",
        "name": "Aric",
        "class": "hero",
        "character": "data/characters/aric.yaml",
    },
    "start": {"map": "town_01_ardel", "position": [12, 8]},
    "bootstrap_flags": ["story_quest_started"],
}

FAKE_CLASS_DATA = {
    "stat_growth": {"hp": [10], "mp": [5], "str": [2], "dex": [2], "con": [2], "int": [2]},
}

FAKE_CHAR_DATA = {
    "hp_max": 50, "mp_max": 20,
    "str": 10, "dex": 8, "con": 9, "int": 6,
    "equipped": {},
}


@pytest.fixture
def saves_dir(tmp_path: Path) -> Path:
    return tmp_path / "saves"


@pytest.fixture
def classes_dir(tmp_path: Path) -> Path:
    d = tmp_path / "classes"
    d.mkdir()
    (d / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
    return d


@pytest.fixture
def manager(saves_dir: Path, classes_dir: Path) -> GameStateManager:
    return GameStateManager(saves_dir=saves_dir, classes_dir=classes_dir)


@pytest.fixture
def state() -> GameState:
    with patch("engine.common.io.game_state_loader._load_class_data", return_value=FAKE_CLASS_DATA), \
         patch("engine.common.io.game_state_loader._load_character_data", return_value=FAKE_CHAR_DATA):
        return from_new_game(
            MANIFEST_STUB, "Aric",
            classes_dir=Path("/fake/classes"),
            scenario_path=Path("/fake/scenario"),
        )


# ── save ──────────────────────────────────────────────────────

class TestSave:
    def test_creates_save_file(self, manager, state, saves_dir):
        path = manager.save(state, slot_index=1)
        assert path.exists()

    def test_autosave_uses_autosave_prefix(self, manager, state, saves_dir):
        path = manager.save(state, slot_index=0)
        assert path.name.startswith("autosave-")

    def test_player_save_uses_save_prefix(self, manager, state, saves_dir):
        path = manager.save(state, slot_index=1)
        assert path.name.startswith("save-")

    def test_autosave_replaces_previous(self, manager, state, saves_dir):
        manager.save(state, slot_index=0)
        manager.save(state, slot_index=0)
        files = list(saves_dir.glob("autosave-*.yaml"))
        assert len(files) == 1

    def test_player_saves_accumulate(self, manager, state, saves_dir):
        manager.save(state, slot_index=1)
        manager.save(state, slot_index=2)
        files = list(saves_dir.glob("save-*.yaml"))
        assert len(files) == 2

    def test_overwrite_replaces_file(self, manager, state, saves_dir):
        path = manager.save(state, slot_index=1)
        manager.save(state, slot_index=1, overwrite_path=path)
        files = list(saves_dir.glob("save-*.yaml"))
        assert len(files) == 1


# ── load ──────────────────────────────────────────────────────

class TestLoad:
    def test_load_restores_flags(self, manager, state, saves_dir):
        state.flags.add_flag("boss_zone01_defeated")
        path = manager.save(state, slot_index=1)
        restored = manager.load(path)
        assert restored.flags.has_flag("story_quest_started")
        assert restored.flags.has_flag("boss_zone01_defeated")

    def test_load_restores_map(self, manager, state, saves_dir):
        path = manager.save(state, slot_index=1)
        restored = manager.load(path)
        assert restored.map.current == "town_01_ardel"

    def test_load_restores_playtime(self, manager, state, saves_dir):
        path = manager.save(state, slot_index=1)
        restored = manager.load(path)
        assert isinstance(restored.playtime.total_seconds, int)


# ── list_slots ────────────────────────────────────────────────

class TestListSlots:
    def test_always_has_autosave_slot(self, manager):
        slots = manager.list_slots()
        assert slots[0].slot_index == 0
        assert slots[0].is_autosave

    def test_empty_dir_has_empty_slots(self, manager):
        slots = manager.list_slots()
        assert all(s.is_empty for s in slots)

    def test_saved_slot_is_not_empty(self, manager, state):
        manager.save(state, slot_index=0)
        slots = manager.list_slots()
        assert not slots[0].is_empty

    def test_player_slot_appears_after_save(self, manager, state):
        manager.save(state, slot_index=1)
        slots = manager.list_slots()
        filled = [s for s in slots if not s.is_empty and not s.is_autosave]
        assert len(filled) == 1

    def test_slot_count_always_101(self, manager):
        slots = manager.list_slots()
        assert len(slots) == 101  # 0=autosave + 100 player
