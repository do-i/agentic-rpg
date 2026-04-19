# tests/unit/core/config/test_engine_config_data.py

import pytest
import yaml
from pathlib import Path
from engine.settings.engine_config_data import EngineConfigData


def write_settings(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "settings.yaml"
    with open(p, "w") as f:
        yaml.dump(data, f)
    return p


_AUDIO = {"bgm_enabled": True, "sfx_enabled": True}
_FONTS = {"sizes": {"small": 12, "medium": 16, "large": 20, "xlarge": 28}}

VALID = {
    "saves": {"dir": "~/user_save_data"},
    "dialogue": {"text_speed": "fast"},
    "audio": _AUDIO,
    "fonts": _FONTS,
}


class TestEngineConfigData:
    def test_loads_saves_dir(self, tmp_path):
        p = write_settings(tmp_path, {**VALID, "saves": {"dir": "/custom/path"}})
        s = EngineConfigData.load(p)
        assert s.saves_dir == "/custom/path"

    def test_loads_text_speed(self, tmp_path):
        p = write_settings(tmp_path, {**VALID, "dialogue": {"text_speed": "slow"}})
        s = EngineConfigData.load(p)
        assert s.text_speed == "slow"

    def test_loads_display_defaults(self, tmp_path):
        p = write_settings(tmp_path, VALID)
        s = EngineConfigData.load(p)
        assert s.screen_width == 1280
        assert s.screen_height == 766
        assert s.fps == 60
        assert s.tile_size == 32

    def test_loads_display_overrides(self, tmp_path):
        p = write_settings(tmp_path, {**VALID,
            "display": {"screen_width": 800, "screen_height": 600, "fps": 30},
            "tiles": {"tile_size": 16},
        })
        s = EngineConfigData.load(p)
        assert s.screen_width == 800
        assert s.screen_height == 600
        assert s.fps == 30
        assert s.tile_size == 16

    def test_raises_when_saves_dir_missing(self, tmp_path):
        p = write_settings(tmp_path, {"dialogue": {"text_speed": "fast"}})
        with pytest.raises(KeyError, match="saves.dir"):
            EngineConfigData.load(p)

    def test_raises_when_text_speed_missing(self, tmp_path):
        p = write_settings(tmp_path, {"saves": {"dir": "~/x"}})
        with pytest.raises(KeyError, match="dialogue.text_speed"):
            EngineConfigData.load(p)

    def test_raises_on_empty_file(self, tmp_path):
        p = tmp_path / "settings.yaml"
        p.write_text("")
        with pytest.raises(KeyError):
            EngineConfigData.load(p)

    def test_is_frozen(self, tmp_path):
        p = write_settings(tmp_path, VALID)
        s = EngineConfigData.load(p)
        with pytest.raises(Exception):
            s.saves_dir = "/new/path"
