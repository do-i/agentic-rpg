# tests/unit/core/dialogue/test_dialogue_engine.py

import pytest
from pathlib import Path
import yaml

from engine.dialogue.dialogue_engine import DialogueEngine
from engine.common.flag_state import FlagState
from engine.party.repository_state import RepositoryState


@pytest.fixture
def dialogue_dir(tmp_path: Path) -> Path:
    return tmp_path / "dialogue"


@pytest.fixture
def engine(dialogue_dir: Path) -> DialogueEngine:
    dialogue_dir.mkdir(parents=True, exist_ok=True)
    return DialogueEngine(dialogue_dir)


def write_dialogue(dialogue_dir: Path, name: str, data: dict) -> None:
    with open(dialogue_dir / f"{name}.yaml", "w") as f:
        yaml.dump(data, f)


# ── resolve ───────────────────────────────────────────────────

class TestResolve:
    def test_returns_none_for_missing_file(self, engine):
        flags = FlagState()
        assert engine.resolve("nonexistent", flags) is None

    def test_first_matching_entry_wins(self, engine, dialogue_dir):
        write_dialogue(dialogue_dir, "npc_test", {
            "type": "npc",
            "entries": [
                {"condition": {"requires": ["flag_b"]}, "lines": ["B line"]},
                {"condition": {"requires": ["flag_a"]}, "lines": ["A line"]},
            ]
        })
        flags = FlagState({"flag_a", "flag_b"})
        result = engine.resolve("npc_test", flags)
        assert result.lines == ["B line"]

    def test_excludes_blocks_entry(self, engine, dialogue_dir):
        write_dialogue(dialogue_dir, "npc_ex", {
            "type": "npc",
            "entries": [
                {
                    "condition": {"requires": ["flag_a"], "excludes": ["flag_b"]},
                    "lines": ["Should not see this"],
                },
                {
                    "condition": {"requires": ["flag_a"]},
                    "lines": ["Fallback"],
                },
            ]
        })
        flags = FlagState({"flag_a", "flag_b"})
        result = engine.resolve("npc_ex", flags)
        assert result.lines == ["Fallback"]

    def test_no_match_returns_none(self, engine, dialogue_dir):
        write_dialogue(dialogue_dir, "npc_none", {
            "type": "npc",
            "entries": [
                {"condition": {"requires": ["missing_flag"]}, "lines": ["Hidden"]},
            ]
        })
        flags = FlagState()
        assert engine.resolve("npc_none", flags) is None

    def test_cutscene_skips_conditions(self, engine, dialogue_dir):
        write_dialogue(dialogue_dir, "intro", {
            "type": "cutscene",
            "lines": ["Line 1", "Line 2"],
        })
        flags = FlagState()
        result = engine.resolve("intro", flags)
        assert result.lines == ["Line 1", "Line 2"]


# ── dispatch_on_complete ──────────────────────────────────────

class TestDispatchOnComplete:
    def test_sets_flag(self, engine):
        flags = FlagState()
        repo = RepositoryState()
        engine.dispatch_on_complete({"set_flag": "boss_defeated"}, flags, repo)
        assert flags.has_flag("boss_defeated")

    def test_sets_multiple_flags(self, engine):
        flags = FlagState()
        repo = RepositoryState()
        engine.dispatch_on_complete({"set_flag": ["flag_a", "flag_b"]}, flags, repo)
        assert flags.has_flag("flag_a")
        assert flags.has_flag("flag_b")

    def test_gives_items(self, engine):
        flags = FlagState()
        repo = RepositoryState()
        engine.dispatch_on_complete(
            {"give_items": [{"id": "potion", "qty": 3}]},
            flags, repo
        )
        assert repo.get_item("potion").qty == 3

    def test_returns_join_party_as_remaining(self, engine):
        flags = FlagState()
        repo = RepositoryState()
        remaining = engine.dispatch_on_complete(
            {"join_party": "elise"}, flags, repo
        )
        assert remaining.get("join_party") == "elise"

    def test_returns_transition_as_remaining(self, engine):
        flags = FlagState()
        repo = RepositoryState()
        t = {"map": "town_02", "position": [5, 5]}
        remaining = engine.dispatch_on_complete({"transition": t}, flags, repo)
        assert remaining.get("transition") == t

    def test_empty_on_complete_returns_empty(self, engine):
        flags = FlagState()
        repo = RepositoryState()
        assert engine.dispatch_on_complete({}, flags, repo) == {}
