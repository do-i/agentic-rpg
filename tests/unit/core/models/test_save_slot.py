# tests/unit/core/models/test_save_slot.py

import pytest
from pathlib import Path
from engine.dto.save_slot import SaveSlot


# ── Properties ────────────────────────────────────────────────

class TestSaveSlotProperties:
    def test_empty_when_no_path(self):
        s = SaveSlot(slot_index=1, path=None)
        assert s.is_empty

    def test_not_empty_when_path_set(self, tmp_path):
        p = tmp_path / "save.yaml"
        p.touch()
        s = SaveSlot(slot_index=1, path=p)
        assert not s.is_empty

    def test_autosave_label(self):
        s = SaveSlot(slot_index=0, path=None, is_autosave=True)
        assert s.label == "Autosave"

    def test_player_slot_label(self):
        s = SaveSlot(slot_index=3, path=None)
        assert s.label == "Slot 03"

    def test_empty_display_line(self):
        s = SaveSlot(slot_index=1, path=None)
        assert "Empty" in s.display_line()

    def test_filled_display_line(self, tmp_path):
        p = tmp_path / "save.yaml"
        p.touch()
        s = SaveSlot(
            slot_index=1,
            path=p,
            protagonist_name="Aric",
            level=12,
            playtime_display="01d 02h 00m",
            location="Ardel",
            timestamp="2024-03-15 14:22",
        )
        line = s.display_line()
        assert "Aric" in line
        assert "Lv12" in line
        assert "Ardel" in line
