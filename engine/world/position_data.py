# engine/dto/position.py

from __future__ import annotations

import math


class Position:
    """
    Immutable 2D tile coordinate value object.
    Owns spatial operations only — no game rules.
    """

    __slots__ = ("x", "y")

    def __init__(self, x: int, y: int) -> None:
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Position is immutable")

    # ── Spatial operations ────────────────────────────────────

    def distance_to(self, other: "Position") -> float:
        """Euclidean distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def offset(self, dx: int, dy: int) -> "Position":
        """Return a new Position shifted by (dx, dy)."""
        return Position(self.x + dx, self.y + dy)

    # ── Value object protocol ─────────────────────────────────

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    # ── Serialization ─────────────────────────────────────────

    def to_list(self) -> list[int]:
        """Serialize to [x, y] for YAML."""
        return [self.x, self.y]

    @classmethod
    def from_list(cls, data: list[int]) -> "Position":
        """Deserialize from [x, y] YAML value."""
        return cls(data[0], data[1])

    def __repr__(self) -> str:
        return f"Position({self.x}, {self.y})"
