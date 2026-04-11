# tests/unit/core/state/test_playtime.py

from datetime import datetime
import pytest
from engine.common.util.clock import FakeClock
from engine.common.util.playtime import Playtime


# ── Construction ──────────────────────────────────────────────

class TestPlaytimeInit:
    def test_default_is_zero(self):
        p = Playtime()
        assert p.total_seconds == 0

    def test_init_with_seconds(self):
        p = Playtime(playtime_seconds=3600)
        assert p.total_seconds == 3600


# ── Session lifecycle ─────────────────────────────────────────

class TestSession:
    def test_commit_accumulates_delta(self):
        clock = FakeClock(datetime(2024, 1, 1, 0, 0, 0))
        p = Playtime(clock=clock)
        p.start_session()
        clock.advance(3600)
        p.commit_session()
        assert p.total_seconds == 3600

    def test_commit_without_start_does_nothing(self):
        p = Playtime()
        p.commit_session()
        assert p.total_seconds == 0

    def test_commit_resets_session_start(self):
        clock = FakeClock(datetime(2024, 1, 1, 0, 0, 0))
        p = Playtime(clock=clock)
        p.start_session()
        clock.advance(1000)
        p.commit_session()
        clock.advance(500)
        p.commit_session()
        assert p.total_seconds == 1500

    def test_prior_seconds_preserved_across_sessions(self):
        clock = FakeClock(datetime(2024, 1, 1, 0, 0, 0))
        p = Playtime(playtime_seconds=100, clock=clock)
        p.start_session()
        clock.advance(200)
        p.commit_session()
        assert p.total_seconds == 300


# ── format ────────────────────────────────────────────────────

class TestFormat:
    def test_zero(self):
        assert Playtime.format(0) == "00d 00h 00m"

    def test_one_hour(self):
        assert Playtime.format(3600) == "00d 01h 00m"

    def test_one_day(self):
        assert Playtime.format(86400) == "01d 00h 00m"

    def test_mixed(self):
        assert Playtime.format(367200) == "04d 06h 00m"

    def test_display_property(self):
        p = Playtime(playtime_seconds=3600)
        assert p.display == "00d 01h 00m"


# ── Serialization ─────────────────────────────────────────────

class TestSerialization:
    def test_to_seconds(self):
        p = Playtime(playtime_seconds=1234)
        assert p.to_seconds() == 1234

    def test_from_seconds(self):
        p = Playtime.from_seconds(5000)
        assert p.total_seconds == 5000

    def test_from_seconds_with_clock(self):
        clock = FakeClock(datetime(2024, 1, 1))
        p = Playtime.from_seconds(100, clock=clock)
        p.start_session()
        clock.advance(50)
        p.commit_session()
        assert p.total_seconds == 150