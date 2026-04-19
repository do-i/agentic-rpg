# engine/settings/engine_config_data.py

from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path
import yaml


SETTINGS_PATH = Path(__file__).parent / "settings.yaml"

_REQUIRED_FONT_SIZES = ("small", "medium", "large", "xlarge")


@dataclass(frozen=True)
class EngineConfigData:
    # display
    screen_width:  int
    screen_height: int
    fps:           int
    # tiles
    tile_size: int
    # runtime
    saves_dir:                    str
    text_speed:                   str
    smooth_collision:             bool
    mc_exchange_confirm_large:    bool
    use_aoe_confirm:              bool
    bgm_enabled:                  bool
    sfx_enabled:                  bool
    debug_party:                  bool
    enemy_spawn_global_interval:  float
    # fonts
    font_sizes: dict[str, int]

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "EngineConfigData":
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        display       = data.get("display") or {}
        tiles         = data.get("tiles")   or {}
        saves_dir     = (data.get("saves")    or {}).get("dir")
        text_speed    = (data.get("dialogue") or {}).get("text_speed")
        smooth        = (data.get("movement")    or {}).get("smooth_collision", True)
        confirm_large = (data.get("shop")        or {}).get("mc_exchange_confirm_large", True)
        use_aoe       = (data.get("item")        or {}).get("use_aoe_confirm", True)
        audio         = data.get("audio") or {}
        bgm_enabled   = audio.get("bgm_enabled")
        sfx_enabled   = audio.get("sfx_enabled")
        debug_party   = (data.get("debug")       or {}).get("party", False)
        global_interval = (data.get("enemy_spawn") or {}).get("global_interval", 30.0)
        fonts_cfg     = data.get("fonts") or {}
        font_sizes    = fonts_cfg.get("sizes") or {}
        missing_sizes = [k for k in _REQUIRED_FONT_SIZES if k not in font_sizes]
        if missing_sizes:
            print(
                f"[ERROR] Missing required font sizes in {path}: "
                f"fonts.sizes.{{{', '.join(missing_sizes)}}}",
                file=sys.stderr,
            )

        missing = []
        if saves_dir is None:
            missing.append("saves.dir")
        if text_speed is None:
            missing.append("dialogue.text_speed")
        if bgm_enabled is None:
            missing.append("audio.bgm_enabled")
        if sfx_enabled is None:
            missing.append("audio.sfx_enabled")
        if missing:
            raise KeyError(
                f"Missing required settings in {path}: {', '.join(missing)}"
            )

        return cls(
            screen_width=display.get("screen_width",  1280),
            screen_height=display.get("screen_height", 766),
            fps=display.get("fps", 60),
            tile_size=tiles.get("tile_size", 32),
            saves_dir=saves_dir,
            text_speed=text_speed,
            smooth_collision=bool(smooth),
            mc_exchange_confirm_large=bool(confirm_large),
            use_aoe_confirm=bool(use_aoe),
            bgm_enabled=bool(bgm_enabled),
            sfx_enabled=bool(sfx_enabled),
            debug_party=bool(debug_party),
            enemy_spawn_global_interval=float(global_interval),
            font_sizes=dict(font_sizes),
        )
