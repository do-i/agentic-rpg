# tests/unit/core/state/test_game_state_holder.py

import pytest
from unittest.mock import patch
from pathlib import Path

from engine.common.game_state_holder import GameStateHolder
from engine.world.position_data import Position
from engine.io.game_state_loader import from_new_game

# ── Shared manifest stub ──────────────────────────────────────

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


def _make_game_state(name="Aric"):
    with patch("engine.io.game_state_loader._load_class_data", return_value=FAKE_CLASS_DATA), \
         patch("engine.io.game_state_loader._load_character_data", return_value=FAKE_CHAR_DATA):
        return from_new_game(
            MANIFEST_STUB, name,
            classes_dir=Path("/fake/classes"),
            scenario_path=Path("/fake/scenario"),
        )


def test_from_new_game_position_is_position_object():
    gs = _make_game_state()
    assert isinstance(gs.map.position, Position)

# ── Construction ──────────────────────────────────────────────

class TestGameStateHolderInit:
    def test_value_is_none_by_default(self):
        h = GameStateHolder()
        assert h.value is None

    def test_not_initialized_by_default(self):
        h = GameStateHolder()
        assert "initialized=False" in repr(h)


# ── get ───────────────────────────────────────────────────────

class TestGet:
    def test_raises_before_set(self):
        h = GameStateHolder()
        with pytest.raises(RuntimeError):
            h.get()

    def test_error_message_is_descriptive(self):
        h = GameStateHolder()
        with pytest.raises(RuntimeError, match="not yet initialized"):
            h.get()

    def test_returns_game_state_after_set(self):
        h = GameStateHolder()
        gs = _make_game_state()
        h.set(gs)
        assert h.get() is gs


# ── set ───────────────────────────────────────────────────────

class TestSet:
    def test_set_updates_value(self):
        h = GameStateHolder()
        gs = _make_game_state()
        h.set(gs)
        assert h.value is gs

    def test_set_can_be_overwritten(self):
        h = GameStateHolder()
        gs1 = _make_game_state("Aric")
        gs2 = _make_game_state("Elise")
        h.set(gs1)
        h.set(gs2)
        assert h.get() is gs2

    def test_initialized_repr_after_set(self):
        h = GameStateHolder()
        gs = _make_game_state()
        h.set(gs)
        assert "initialized=True" in repr(h)
