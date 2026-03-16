# engine/core/models/clock.py

from datetime import datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """
    Protocol — defines the contract for time providers.
    Structural typing: any class with now() -> datetime satisfies this.
    No explicit inheritance required.
    """

    def now(self) -> datetime:
        ...


class SystemClock:
    """Production implementation — delegates to real system time."""

    def now(self) -> datetime:
        return datetime.now()


class FakeClock:
    """
    Test implementation — fully deterministic.
    Advance time explicitly via advance() to control test scenarios.

    Usage:
        clock = FakeClock(datetime(2024, 1, 1, 0, 0, 0))
        p = Playtime(clock=clock)
        p.start_session()
        clock.advance(3600)
        p.commit_session()
        assert p.total_seconds == 3600
    """

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        """Move the clock forward by the given number of seconds."""
        self._now += timedelta(seconds=seconds)
