# tests/unit/quest/test_quest_catalog.py

import pytest

from engine.common.flag_state import FlagState
from engine.quest.quest_catalog import (
    QuestCatalog,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
)


VALID_ENTRY = """\
- id: sq_example
  name: "An Example Errand"
  type: sub
  location: Ardel
  description: "Carry word across town."
  started_flag: sq_example_started
  completed_flag: sq_example_done
"""


def _write(tmp_path, text):
    path = tmp_path / "quests.yaml"
    path.write_text(text)
    return path


class TestLoading:
    def test_loads_quest_fields(self, tmp_path):
        catalog = QuestCatalog(_write(tmp_path, VALID_ENTRY))
        assert len(catalog.quests) == 1
        quest = catalog.quests[0]
        assert quest.id == "sq_example"
        assert quest.type == "sub"
        assert quest.started_flag == "sq_example_started"
        assert quest.completed_flag == "sq_example_done"

    def test_preserves_declaration_order(self, tmp_path):
        text = VALID_ENTRY + VALID_ENTRY.replace("sq_example", "sq_other")
        catalog = QuestCatalog(_write(tmp_path, text))
        assert [q.id for q in catalog.quests] == ["sq_example", "sq_other"]

    def test_missing_field_raises(self, tmp_path):
        text = VALID_ENTRY.replace("  location: Ardel\n", "")
        with pytest.raises(ValueError, match="location"):
            QuestCatalog(_write(tmp_path, text))

    def test_bad_type_raises(self, tmp_path):
        text = VALID_ENTRY.replace("type: sub", "type: side")
        with pytest.raises(ValueError, match="side"):
            QuestCatalog(_write(tmp_path, text))

    def test_duplicate_id_raises(self, tmp_path):
        with pytest.raises(ValueError, match="duplicate"):
            QuestCatalog(_write(tmp_path, VALID_ENTRY + VALID_ENTRY))

    def test_empty_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="non-empty"):
            QuestCatalog(_write(tmp_path, "[]\n"))


class TestStatus:
    def _quest(self, tmp_path):
        return QuestCatalog(_write(tmp_path, VALID_ENTRY)).quests[0]

    def test_not_started(self, tmp_path):
        quest = self._quest(tmp_path)
        assert QuestCatalog.status(quest, FlagState()) == STATUS_NOT_STARTED

    def test_in_progress(self, tmp_path):
        quest = self._quest(tmp_path)
        flags = FlagState({"sq_example_started"})
        assert QuestCatalog.status(quest, flags) == STATUS_IN_PROGRESS

    def test_completed(self, tmp_path):
        quest = self._quest(tmp_path)
        flags = FlagState({"sq_example_started", "sq_example_done"})
        assert QuestCatalog.status(quest, flags) == STATUS_COMPLETED

    def test_completed_flag_alone_is_completed(self, tmp_path):
        quest = self._quest(tmp_path)
        flags = FlagState({"sq_example_done"})
        assert QuestCatalog.status(quest, flags) == STATUS_COMPLETED
