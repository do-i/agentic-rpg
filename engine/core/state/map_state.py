# engine/core/state/map_state.py


class MapState:
    """
    Tracks the current map, player position, and visited map history.
    Position is a [col, row] tile coordinate.
    """

    def __init__(
        self,
        current: str = "",
        position: list[int] | None = None,
        visited: list[str] | None = None,
    ) -> None:
        self.current: str = current
        self.position: list[int] = position if position is not None else [0, 0]
        self._visited: list[str] = visited if visited is not None else []

    # ── Mutation ──────────────────────────────────────────────

    def move_to(self, map_id: str, position: list[int]) -> None:
        """Switch to a new map and record it as visited."""
        if self.current and self.current not in self._visited:
            self._visited.append(self.current)
        self.current = map_id
        self.position = position

    def set_position(self, position: list[int]) -> None:
        """Update position within the current map."""
        self.position = position

    # ── Query ─────────────────────────────────────────────────

    def has_visited(self, map_id: str) -> bool:
        return map_id in self._visited

    @property
    def visited(self) -> list[str]:
        return list(self._visited)

    # ── Serialization ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "position": self.position,
            "visited": list(self._visited),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MapState":
        return cls(
            current=data.get("current", ""),
            position=data.get("position", [0, 0]),
            visited=data.get("visited", []),
        )

    def __repr__(self) -> str:
        return f"MapState(current={self.current!r}, position={self.position})"
