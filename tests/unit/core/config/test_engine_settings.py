# tests/unit/core/config/test_engine_settings.py

import pytest
import yaml
from pathlib import Path
from engine.core.config.engine_settings import EngineSettings


def write_settings(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "settings.yaml"
    with open(p, "w") as f:
        yaml.dump(data, f)
    return p


VALID = {
    "saves": {"dir": "~/user_save_data"},
    "dialogue": {"text_speed": "fast"},
}


class TestEngineSettings:
    def test_loads_saves_dir(self, tmp_path):
        p = write_settings(tmp_path, {"saves": {"dir": "/custom/path"}, "dialogue": {"text_speed": "fast"}})
        s = EngineSettings.load(p)
        assert s.saves_dir == "/custom/path"

    def test_loads_text_speed(self, tmp_path):
        p = write_settings(tmp_path, {"saves": {"dir": "~/x"}, "dialogue": {"text_speed": "slow"}})
        s = EngineSettings.load(p)
        assert s.text_speed == "slow"

    def test_raises_when_saves_dir_missing(self, tmp_path):
        p = write_settings(tmp_path, {"dialogue": {"text_speed": "fast"}})
        with pytest.raises(KeyError, match="saves.dir"):
            EngineSettings.load(p)

    def test_raises_when_text_speed_missing(self, tmp_path):
        p = write_settings(tmp_path, {"saves": {"dir": "~/x"}})
        with pytest.raises(KeyError, match="dialogue.text_speed"):
            EngineSettings.load(p)

    def test_raises_when_both_missing(self, tmp_path):
        p = write_settings(tmp_path, {})
        with pytest.raises(KeyError, match="saves.dir"):
            EngineSettings.load(p)

    def test_raises_on_empty_file(self, tmp_path):
        p = tmp_path / "settings.yaml"
        p.write_text("")
        with pytest.raises(KeyError):
            EngineSettings.load(p)

    def test_is_frozen(self, tmp_path):
        p = write_settings(tmp_path, VALID)
        s = EngineSettings.load(p)
        with pytest.raises(Exception):
            s.saves_dir = "/new/path"
