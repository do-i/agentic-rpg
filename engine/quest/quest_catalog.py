# engine/quest/quest_catalog.py
#
# Loads the scenario quest registry (data/quests.yaml) and derives each
# quest's board status from the current flag state. Pure data + lookup;
# rendering lives in quest_board_scene.py.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.common.flag_state import FlagState
from engine.io.yaml_loader import load_yaml_required

QUEST_TYPE_MAIN = "main"
QUEST_TYPE_SUB = "sub"
_QUEST_TYPES = (QUEST_TYPE_MAIN, QUEST_TYPE_SUB)

STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"

_REQUIRED_FIELDS = (
    "id", "name", "type", "location", "description",
    "started_flag", "completed_flag",
)


@dataclass(frozen=True)
class QuestDef:
    """Read-only quest registry entry loaded from scenario YAML."""
    id: str
    name: str
    type: str            # main | sub
    location: str
    description: str
    started_flag: str
    completed_flag: str


class QuestCatalog:
    """All quests in scenario declaration order (main quests first by
    convention of the YAML file, but no reordering happens here)."""

    def __init__(self, quests_path: Path) -> None:
        entries = load_yaml_required(quests_path)
        if not isinstance(entries, list) or not entries:
            raise ValueError(
                f"{quests_path}: expected a non-empty list of quest entries. "
                f"Example:\n- id: sq_example\n  name: \"An Example Errand\"\n"
                f"  type: sub\n  location: Ardel\n  description: \"...\"\n"
                f"  started_flag: sq_example_started\n"
                f"  completed_flag: sq_example_done"
            )
        quests: list[QuestDef] = []
        seen: set[str] = set()
        for entry in entries:
            for field_name in _REQUIRED_FIELDS:
                if entry.get(field_name) is None:
                    raise ValueError(
                        f"{quests_path}: quest entry {entry.get('id', entry)!r} is "
                        f"missing required field '{field_name}'. Define it under the "
                        f"entry (e.g. {field_name}: sq_example_started)."
                    )
            if entry["type"] not in _QUEST_TYPES:
                raise ValueError(
                    f"{quests_path}: quest {entry['id']!r} has type "
                    f"{entry['type']!r}; expected one of {_QUEST_TYPES}."
                )
            if entry["id"] in seen:
                raise ValueError(
                    f"{quests_path}: duplicate quest id {entry['id']!r}."
                )
            seen.add(entry["id"])
            quests.append(QuestDef(
                id=entry["id"],
                name=entry["name"],
                type=entry["type"],
                location=entry["location"],
                description=entry["description"],
                started_flag=entry["started_flag"],
                completed_flag=entry["completed_flag"],
            ))
        self._quests: tuple[QuestDef, ...] = tuple(quests)

    @property
    def quests(self) -> tuple[QuestDef, ...]:
        return self._quests

    @staticmethod
    def status(quest: QuestDef, flags: FlagState) -> str:
        """Board status for one quest under the given flag state."""
        if flags.has_flag(quest.completed_flag):
            return STATUS_COMPLETED
        if flags.has_flag(quest.started_flag):
            return STATUS_IN_PROGRESS
        return STATUS_NOT_STARTED
