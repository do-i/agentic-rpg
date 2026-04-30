# engine/common/opened_boxes_state.py


from __future__ import annotations

class OpenedBoxesState:
    """
    Tracks which item boxes the party has already opened.
    Keyed by (map_id, box_id) — box ids are unique within a map.
    Serialized as a list of "map_id:box_id" strings for save files.
    """

    def __init__(self, opened: set[tuple[str, str]] | None = None) -> None:
        self._opened: set[tuple[str, str]] = set(opened) if opened else set()

    # -- Query --

    def is_opened(self, map_id: str, box_id: str) -> bool:
        return (map_id, box_id) in self._opened

    # -- Mutation --

    def mark_opened(self, map_id: str, box_id: str) -> None:
        self._opened.add((map_id, box_id))

    # -- Serialization --

    def to_list(self) -> list[str]:
        return sorted(f"{m}:{b}" for (m, b) in self._opened)

    @classmethod
    def from_list(cls, entries: list[str] | None) -> "OpenedBoxesState":
        opened: set[tuple[str, str]] = set()
        for item in entries or []:
            if ":" not in item:
                continue
            map_id, box_id = item.split(":", 1)
            opened.add((map_id, box_id))
        return cls(opened)

    def __repr__(self) -> str:
        return f"OpenedBoxesState({self.to_list()})"
