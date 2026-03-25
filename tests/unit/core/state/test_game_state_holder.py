# tests/unit/core/state/test_game_state_holder.py

import pytest
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.game_state import GameState
from engine.core.models.position import Position

# ── Shared manifest stub ──────────────────────────────────────

MANIFEST_STUB = {
    "protagonist": {"id": "aric", "name": "Aric"},
    "start": {"map": "town_01_ardel", "position": [12, 8]},
    "bootstrap_flags": ["story_quest_started"],
}

def test_from_new_game_position_is_position_object():
    gs = GameState.from_new_game(MANIFEST_STUB, "Aric")
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
        gs = GameState.from_new_game(MANIFEST_STUB, "Aric")
        h.set(gs)
        assert h.get() is gs


# ── set ───────────────────────────────────────────────────────

class TestSet:
    def test_set_updates_value(self):
        h = GameStateHolder()
        gs = GameState.from_new_game(MANIFEST_STUB, "Aric")
        h.set(gs)
        assert h.value is gs

    def test_set_can_be_overwritten(self):
        h = GameStateHolder()
        gs1 = GameState.from_new_game(MANIFEST_STUB, "Aric")
        gs2 = GameState.from_new_game(MANIFEST_STUB, "Elise")
        h.set(gs1)
        h.set(gs2)
        assert h.get() is gs2

    def test_initialized_repr_after_set(self):
        h = GameStateHolder()
        gs = GameState.from_new_game(MANIFEST_STUB, "Aric")
        h.set(gs)
        assert "initialized=True" in repr(h)