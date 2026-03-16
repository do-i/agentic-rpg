# tests/unit/core/state/test_flag_state.py

import pytest
from engine.core.state.flag_state import FlagState


# ── Construction ──────────────────────────────────────────────

class TestFlagStateInit:
    def test_empty_by_default(self):
        f = FlagState()
        assert f.to_list() == []

    def test_init_with_set(self):
        f = FlagState({"flag_a", "flag_b"})
        assert f.has_flag("flag_a")
        assert f.has_flag("flag_b")

    def test_init_deduplicates(self):
        f = FlagState({"flag_a", "flag_a"})
        assert f.to_list().count("flag_a") == 1


# ── add_flag ──────────────────────────────────────────────────

class TestAddFlag:
    def test_adds_flag(self):
        f = FlagState()
        f.add_flag("story_quest_started")
        assert f.has_flag("story_quest_started")

    def test_duplicate_is_ignored(self):
        f = FlagState()
        f.add_flag("flag_a")
        f.add_flag("flag_a")
        assert f.to_list().count("flag_a") == 1

    def test_never_cleared(self):
        f = FlagState()
        f.add_flag("flag_a")
        f.add_flag("flag_a")  # re-adding does not clear
        assert f.has_flag("flag_a")


# ── add_flags ─────────────────────────────────────────────────

class TestAddFlags:
    def test_adds_multiple_from_list(self):
        f = FlagState()
        f.add_flags(["flag_a", "flag_b", "flag_c"])
        assert f.has_flag("flag_a")
        assert f.has_flag("flag_b")
        assert f.has_flag("flag_c")

    def test_adds_multiple_from_set(self):
        f = FlagState()
        f.add_flags({"flag_a", "flag_b"})
        assert f.has_flag("flag_a")
        assert f.has_flag("flag_b")

    def test_deduplicates_across_calls(self):
        f = FlagState()
        f.add_flags(["flag_a", "flag_b"])
        f.add_flags(["flag_b", "flag_c"])
        assert f.to_list().count("flag_b") == 1


# ── has_flag ──────────────────────────────────────────────────

class TestHasFlag:
    def test_true_for_existing_flag(self):
        f = FlagState({"flag_a"})
        assert f.has_flag("flag_a")

    def test_false_for_missing_flag(self):
        f = FlagState()
        assert not f.has_flag("flag_a")


# ── has_all ───────────────────────────────────────────────────

class TestHasAll:
    def test_true_when_all_present(self):
        f = FlagState({"flag_a", "flag_b", "flag_c"})
        assert f.has_all(["flag_a", "flag_b"])

    def test_false_when_one_missing(self):
        f = FlagState({"flag_a"})
        assert not f.has_all(["flag_a", "flag_b"])

    def test_empty_list_is_true(self):
        f = FlagState()
        assert f.has_all([])


# ── has_any ───────────────────────────────────────────────────

class TestHasAny:
    def test_true_when_one_present(self):
        f = FlagState({"flag_a"})
        assert f.has_any(["flag_a", "flag_b"])

    def test_false_when_none_present(self):
        f = FlagState()
        assert not f.has_any(["flag_a", "flag_b"])

    def test_empty_list_is_false(self):
        f = FlagState({"flag_a"})
        assert not f.has_any([])

    def test_empty_list_is_true(self):
        f = FlagState()
        assert not f.has_any([])


# ── has_none ──────────────────────────────────────────────────

class TestHasNone:
    def test_true_when_none_present(self):
        f = FlagState({"flag_a"})
        assert f.has_none(["flag_b", "flag_c"])

    def test_false_when_one_present(self):
        f = FlagState({"flag_a", "flag_b"})
        assert not f.has_none(["flag_b"])

    def test_empty_list_is_true(self):
        f = FlagState({"flag_a"})
        assert f.has_none([])


# ── Serialization ─────────────────────────────────────────────

class TestSerialization:
    def test_to_list_is_sorted(self):
        f = FlagState({"flag_c", "flag_a", "flag_b"})
        assert f.to_list() == ["flag_a", "flag_b", "flag_c"]

    def test_from_set_round_trip(self):
        original = {"flag_a", "flag_b", "flag_c"}
        f = FlagState.from_set(original)
        assert set(f.to_list()) == original

    def test_empty_round_trip(self):
        f = FlagState.from_set(set())
        assert f.to_list() == []