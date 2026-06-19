# engine/dto/map_state.py

from __future__ import annotations

from engine.world.position_data import Position
from engine.world.sprite_sheet import Direction


class MapState:
    """
    Tracks the current map, player position, and visited map history.
    """

    def __init__(
        self,
        current: str = "",
        position: Position | None = None,
        visited: set[str] | None = None,
        display_name: str = "",
    ) -> None:
        self.current: str = current
        self.display_name: str = display_name
        self.position: Position = position if position is not None else Position(0, 0)
        self._visited: set[str] = set(visited) if visited is not None else set()
        # Direction the player should face on arrival at the current map.
        # Transient (not serialized): set by move_to, consumed when the world
        # scene builds the Player. Defaults to facing south.
        self.facing: Direction = Direction.DOWN

    # -- Mutation --

    def move_to(self, map_id: str, position: Position, facing: Direction) -> None:
        """Switch to a new map and record previous as visited.

        ``facing`` is the direction the player should face on arrival — for a
        portal this is the direction of travel through the door, so the player
        ends up facing away from the entrance rather than always facing south.
        """
        if self.current and self.current not in self._visited:
            self._visited.add(self.current)
        self.current = map_id
        self.position = position
        self.facing = facing

    def set_position(self, position: Position) -> None:
        """Update position within the current map."""
        self.position = position

    # -- Query --

    def has_visited(self, map_id: str) -> bool:
        return map_id in self._visited

    @property
    def visited(self) -> list[str]:
        return sorted(self._visited)

    # -- Serialization --

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "position": self.position.to_list(),
            "visited": sorted(self._visited),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MapState":
        for field in ("current", "position", "visited"):
            if field not in data:
                raise ValueError(
                    f"MapState.from_dict: save data missing required field {field!r}. "
                    f"Got keys: {sorted(data)}. "
                    f"Example:\n  current: town_01\n  position: [5, 3]\n  visited: [zone_01]"
                )
        return cls(
            current=data["current"],
            position=Position.from_list(data["position"]),
            visited=set(data["visited"]),
        )

    def __repr__(self) -> str:
        return f"MapState(current={self.current!r}, position={sorted(self.position)})"
