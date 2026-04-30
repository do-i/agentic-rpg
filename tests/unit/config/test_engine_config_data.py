# tests/unit/core/config/test_engine_config_data.py

from __future__ import annotations

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
    "display": {"screen_width": 1280, "screen_height": 766, "fps": 60},
    "tiles": {"tile_size": 32},
    "saves": {"dir": "~/user_save_data"},
    "dialogue": {"text_speed": "fast"},
    "movement": {"smooth_collision": True},
    "shop": {"mc_exchange_confirm_large": True},
    "item": {"use_aoe_confirm": True},
    "audio": _AUDIO,
    "fonts": _FONTS,
    "enemy_spawn": {"global_interval": 30.0},
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

    def test_loads_display(self, tmp_path):
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
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "saves"})
        with pytest.raises(KeyError, match="saves.dir"):
            EngineConfigData.load(p)

    def test_raises_when_text_speed_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "dialogue"})
        with pytest.raises(KeyError, match="dialogue.text_speed"):
            EngineConfigData.load(p)

    def test_raises_when_display_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "display"})
        with pytest.raises(KeyError, match="display.screen_width"):
            EngineConfigData.load(p)

    def test_raises_when_tile_size_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "tiles"})
        with pytest.raises(KeyError, match="tiles.tile_size"):
            EngineConfigData.load(p)

    def test_raises_when_smooth_collision_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "movement"})
        with pytest.raises(KeyError, match="movement.smooth_collision"):
            EngineConfigData.load(p)

    def test_raises_when_mc_exchange_confirm_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "shop"})
        with pytest.raises(KeyError, match="shop.mc_exchange_confirm_large"):
            EngineConfigData.load(p)

    def test_raises_when_use_aoe_confirm_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "item"})
        with pytest.raises(KeyError, match="item.use_aoe_confirm"):
            EngineConfigData.load(p)

    def test_raises_when_global_interval_missing(self, tmp_path):
        p = write_settings(tmp_path, {k: v for k, v in VALID.items() if k != "enemy_spawn"})
        with pytest.raises(KeyError, match="enemy_spawn.global_interval"):
            EngineConfigData.load(p)

    def test_debug_block_is_optional(self, tmp_path):
        p = write_settings(tmp_path, VALID)
        s = EngineConfigData.load(p)
        assert s.debug_party is False
        assert s.debug_collision is False

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
