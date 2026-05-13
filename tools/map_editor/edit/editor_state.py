"""State machine for the 4-step portal-retarget wizard.

Mirrors the editor flow from maps_graph.html:

    source_node  → graph: click the source map's node
    source_tile  → modal: click a portal tile on the source map
    dest_node    → graph: click the destination map's node
    dest_tile    → modal: click any tile on the destination map  →  recorded edit

After recording an edit the wizard cycles back to source_node so the user can
retarget another portal. Edits are accumulated in-memory until the user
explicitly saves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


STEP_IDLE = "idle"
STEP_SOURCE_NODE = "source_node"
STEP_SOURCE_TILE = "source_tile"
STEP_DEST_NODE = "dest_node"
STEP_DEST_TILE = "dest_tile"


@dataclass
class PortalEdit:
    source_tmx: Path
    source_map_id: str
    portal_obj_id: int
    original_target_map: str
    original_target_tile: tuple[int, int]
    new_target_map: str
    new_target_tile: tuple[int, int]

    @property
    def changed(self) -> bool:
        return (
            self.original_target_map != self.new_target_map
            or self.original_target_tile != self.new_target_tile
        )

    def describe(self) -> str:
        return (
            f"{self.source_map_id} #{self.portal_obj_id}  "
            f"{self.original_target_map}@{self.original_target_tile[0]},{self.original_target_tile[1]} "
            f"→  {self.new_target_map}@{self.new_target_tile[0]},{self.new_target_tile[1]}"
        )


@dataclass
class EditorState:
    enabled: bool = False
    step: str = STEP_IDLE
    source_map: str | None = None
    source_portal_obj_id: int | None = None
    source_portal_tile: tuple[int, int] | None = None
    original_target_map: str | None = None
    original_target_tile: tuple[int, int] | None = None
    dest_map: str | None = None
    # Keyed by (source_map, portal_obj_id) so re-editing the same portal replaces.
    pending: dict[tuple[str, int], PortalEdit] = field(default_factory=dict)
    last_message: str = ""

    def enable(self) -> None:
        self.enabled = True
        self.step = STEP_SOURCE_NODE
        self._clear_cycle()
        self.last_message = "Edit mode: select source map node"

    def disable(self) -> None:
        self.enabled = False
        self.step = STEP_IDLE
        self._clear_cycle()
        self.last_message = ""

    def _clear_cycle(self) -> None:
        self.source_map = None
        self.source_portal_obj_id = None
        self.source_portal_tile = None
        self.original_target_map = None
        self.original_target_tile = None
        self.dest_map = None

    def step_label(self) -> str:
        return {
            STEP_SOURCE_NODE: "1/4 Select source map node",
            STEP_SOURCE_TILE: f"2/4 Click a portal tile on {self.source_map}",
            STEP_DEST_NODE: "3/4 Select destination map node",
            STEP_DEST_TILE: f"4/4 Click arrival tile on {self.dest_map}",
        }.get(self.step, "")

    def set_source_map(self, map_id: str) -> None:
        self.source_map = map_id
        self.step = STEP_SOURCE_TILE
        self.last_message = ""

    def set_source_portal(
        self,
        portal_obj_id: int,
        source_tile: tuple[int, int],
        original_target_map: str,
        original_target_tile: tuple[int, int],
    ) -> None:
        self.source_portal_obj_id = portal_obj_id
        self.source_portal_tile = source_tile
        self.original_target_map = original_target_map
        self.original_target_tile = original_target_tile
        self.step = STEP_DEST_NODE
        self.last_message = (
            f"Source: {self.source_map} #{portal_obj_id} "
            f"(was → {original_target_map}@{original_target_tile[0]},{original_target_tile[1]})"
        )

    def set_dest_map(self, map_id: str) -> None:
        self.dest_map = map_id
        self.step = STEP_DEST_TILE
        self.last_message = ""

    def record_edit(self, source_tmx: Path, dest_tile: tuple[int, int]) -> PortalEdit:
        assert self.source_map is not None
        assert self.source_portal_obj_id is not None
        assert self.source_portal_tile is not None
        assert self.dest_map is not None
        assert self.original_target_map is not None
        assert self.original_target_tile is not None
        edit = PortalEdit(
            source_tmx=source_tmx,
            source_map_id=self.source_map,
            portal_obj_id=self.source_portal_obj_id,
            original_target_map=self.original_target_map,
            original_target_tile=self.original_target_tile,
            new_target_map=self.dest_map,
            new_target_tile=dest_tile,
        )
        key = (edit.source_map_id, edit.portal_obj_id)
        if edit.changed:
            self.pending[key] = edit
        else:
            self.pending.pop(key, None)
        self.last_message = "Saved (pending): " + edit.describe()
        self._next_cycle()
        return edit

    def _next_cycle(self) -> None:
        self.step = STEP_SOURCE_NODE
        self._clear_cycle()

    def cancel_cycle(self, message: str = "") -> None:
        if not self.enabled:
            return
        self.step = STEP_SOURCE_NODE
        self._clear_cycle()
        if message:
            self.last_message = message

    def discard_all(self) -> None:
        self.pending.clear()
        self.last_message = "Pending edits cleared"
