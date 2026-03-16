# engine/core/state/map_state.py

from engine.core.models.position import Position


class MapState:
    """
    Tracks the current map, player position, and visited map history.
    """

    def __init__(
        self,
        current: str = "",
        position: Position | None = None,
        visited: set[str] | None = None,
    ) -> None:
        self.current: str = current
        self.position: Position = position if position is not None else Position(0, 0)
        self._visited: set[str] = visited if visited is not None else []

    # ── Mutation ──────────────────────────────────────────────

    def move_to(self, map_id: str, position: Position) -> None:
        """Switch to a new map and record previous as visited."""
        if self.current and self.current not in self._visited:
            self._visited.append(self.current)
        self.current = map_id
        self.position = position

    def set_position(self, position: Position) -> None:
        """Update position within the current map."""
        self.position = position

    # ── Query ─────────────────────────────────────────────────

    def has_visited(self, map_id: str) -> bool:
        return map_id in self._visited

    @property
    def visited(self) -> list[str]:
        return sorted(self._visited)

    # ── Serialization ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "position": self.position.to_list(),
            "visited": sorted(self._visited),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MapState":
        raw_pos = data.get("position", [0, 0])
        return cls(
            current=data.get("current", ""),
            position=Position.from_list(raw_pos),
            visited=set(data.get("visited", [])),
        )

    def __repr__(self) -> str:
        return f"MapState(current={self.current!r}, position={sorted(self.position)})"
