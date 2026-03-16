# engine/core/state/playtime.py

from datetime import datetime

"""
Review Feedback
Hard to write unit test if non-deterministic object such as datetime.now() is embedded.
Think alternative way -- injecting SystemClock service.
"""
class Playtime:
    """
    Tracks cumulative playtime across sessions.
    session_start is in-memory only — never serialized.
    """

    def __init__(self, playtime_seconds: int = 0) -> None:
        self._playtime_seconds: int = playtime_seconds
        self._session_start: datetime | None = None

    # ── Session lifecycle ─────────────────────────────────────

    def start_session(self) -> None:
        self._session_start = datetime.now()

    def commit_session(self) -> None:
        """Call on save — accumulates session delta into total."""
        if self._session_start is not None:
            delta = (datetime.now() - self._session_start).seconds
            self._playtime_seconds += delta
            self._session_start = datetime.now()  # reset for next segment

    # ── Query ─────────────────────────────────────────────────

    @property
    def total_seconds(self) -> int:
        return self._playtime_seconds

    @staticmethod
    def format(seconds: int) -> str:
        """Returns formatted string e.g. '04d 06h 00m'."""
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        m = (seconds % 3600) // 60
        return f"{d:02d}d {h:02d}h {m:02d}m"

    @property
    def display(self) -> str:
        return self.format(self._playtime_seconds)

    # ── Serialization ─────────────────────────────────────────

    def to_seconds(self) -> int:
        return self._playtime_seconds

    @classmethod
    def from_seconds(cls, seconds: int) -> "Playtime":
        return cls(playtime_seconds=seconds)

    def __repr__(self) -> str:
        return f"Playtime({self.display})"
