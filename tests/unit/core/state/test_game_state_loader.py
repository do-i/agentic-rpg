# tests/unit/core/state/test_game_state_loader.py

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from engine.io.game_state_loader import (
    from_save, _load_class_data, _load_character_data,
)

FAKE_CLASS_DATA = {
    "stat_growth": {"hp": [10], "mp": [5], "str": [2], "dex": [2], "con": [2], "int": [2]},
    "abilities": [],
}

FAKE_CHAR_DATA = {
    "hp_max": 50, "mp_max": 20,
    "str": 10, "dex": 8, "con": 9, "int": 6,
    "equipped": {},
}


def _minimal_save(*, exp_next=100, items=None, gp=0):
    """Build a minimal valid save dict for from_save."""
    return {
        "flags": ["story_started"],
        "map": {"current": "map_01", "position": [5, 3], "visited": []},
        "meta": {"playtime_seconds": 60},
        "party": [{
            "id": "aric",
            "name": "Aric",
            "protagonist": True,
            "class": "hero",
            "level": 2,
            "exp": 50,
            "exp_next": exp_next,
            "hp": 45, "hp_max": 50,
            "mp": 18, "mp_max": 20,
            "str": 11, "dex": 9, "con": 10, "int": 7,
            "equipped": {},
        }],
        "party_repository": {
            "gp": gp,
            "items": items or [],
        },
    }


# ── _load_class_data ──────────────────────────────────────────

class TestLoadClassData:
    def test_raises_when_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _load_class_data(tmp_path, "hero")

    def test_loads_yaml_content(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        data = _load_class_data(tmp_path, "hero")
        assert "stat_growth" in data


# ── _load_character_data ──────────────────────────────────────

class TestLoadCharacterData:
    def test_raises_when_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _load_character_data(tmp_path, "data/characters/aric.yaml")

    def test_loads_yaml_content(self, tmp_path):
        char_dir = tmp_path / "data" / "characters"
        char_dir.mkdir(parents=True)
        (char_dir / "aric.yaml").write_text(yaml.dump(FAKE_CHAR_DATA))
        data = _load_character_data(tmp_path, "data/characters/aric.yaml")
        assert data["hp_max"] == 50


# ── from_save — exp_next fallback ─────────────────────────────

class TestFromSaveExpNext:
    def test_calculates_exp_next_when_absent_from_save(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        save = _minimal_save()
        del save["party"][0]["exp_next"]  # remove so from_save must calculate it

        state = from_save(save, classes_dir=tmp_path)
        assert state.party.members[0].exp_next > 0

    def test_uses_provided_exp_next_when_present(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        state = from_save(_minimal_save(exp_next=999), classes_dir=tmp_path)
        assert state.party.members[0].exp_next == 999


# ── from_save — items ─────────────────────────────────────────

class TestFromSaveItems:
    def test_loads_regular_item(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        items = [{"id": "potion", "qty": 3, "tags": [], "locked": False}]
        state = from_save(_minimal_save(items=items), classes_dir=tmp_path)
        entry = next(e for e in state.repository.items if e.id == "potion")
        assert entry.qty == 3
        assert not entry.locked

    def test_mc_item_gets_magic_core_tag(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        items = [{"id": "mc_s", "qty": 2, "tags": [], "locked": False}]
        state = from_save(_minimal_save(items=items), classes_dir=tmp_path)
        entry = next(e for e in state.repository.items if e.id == "mc_s")
        assert "magic_core" in entry.tags

    def test_locked_item_is_locked(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        items = [{"id": "key_item", "qty": 1, "tags": ["key"], "locked": True}]
        state = from_save(_minimal_save(items=items), classes_dir=tmp_path)
        entry = next(e for e in state.repository.items if e.id == "key_item")
        assert entry.locked
        assert "key" in entry.tags

    def test_item_without_id_is_skipped(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        items = [{"qty": 1}]  # no id
        state = from_save(_minimal_save(items=items), classes_dir=tmp_path)
        assert len(state.repository.items) == 0

    def test_gp_is_restored(self, tmp_path):
        (tmp_path / "hero.yaml").write_text(yaml.dump(FAKE_CLASS_DATA))
        state = from_save(_minimal_save(gp=250), classes_dir=tmp_path)
        assert state.repository.gp == 250
