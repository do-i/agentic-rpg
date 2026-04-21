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
    debug_collision:              bool
    enemy_spawn_global_interval:  float
    # fonts
    font_sizes: dict[str, int]

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "EngineConfigData":
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        display       = data.get("display") or {}
        tiles         = data.get("tiles")   or {}
        screen_width  = display.get("screen_width")
        screen_height = display.get("screen_height")
        fps           = display.get("fps")
        tile_size     = tiles.get("tile_size")
        saves_dir     = (data.get("saves")    or {}).get("dir")
        text_speed    = (data.get("dialogue") or {}).get("text_speed")
        smooth        = (data.get("movement") or {}).get("smooth_collision")
        confirm_large = (data.get("shop")     or {}).get("mc_exchange_confirm_large")
        use_aoe       = (data.get("item")     or {}).get("use_aoe_confirm")
        audio         = data.get("audio") or {}
        bgm_enabled   = audio.get("bgm_enabled")
        sfx_enabled   = audio.get("sfx_enabled")
        debug_cfg     = data.get("debug") or {}
        debug_party   = debug_cfg.get("party", False)
        debug_coll    = debug_cfg.get("collision", False)
        global_interval = (data.get("enemy_spawn") or {}).get("global_interval")
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
        if screen_width is None:
            missing.append("display.screen_width")
        if screen_height is None:
            missing.append("display.screen_height")
        if fps is None:
            missing.append("display.fps")
        if tile_size is None:
            missing.append("tiles.tile_size")
        if saves_dir is None:
            missing.append("saves.dir")
        if text_speed is None:
            missing.append("dialogue.text_speed")
        if smooth is None:
            missing.append("movement.smooth_collision")
        if confirm_large is None:
            missing.append("shop.mc_exchange_confirm_large")
        if use_aoe is None:
            missing.append("item.use_aoe_confirm")
        if bgm_enabled is None:
            missing.append("audio.bgm_enabled")
        if sfx_enabled is None:
            missing.append("audio.sfx_enabled")
        if global_interval is None:
            missing.append("enemy_spawn.global_interval")
        if missing:
            raise KeyError(
                f"Missing required settings in {path}: {', '.join(missing)}"
            )

        return cls(
            screen_width=screen_width,
            screen_height=screen_height,
            fps=fps,
            tile_size=tile_size,
            saves_dir=saves_dir,
            text_speed=text_speed,
            smooth_collision=bool(smooth),
            mc_exchange_confirm_large=bool(confirm_large),
            use_aoe_confirm=bool(use_aoe),
            bgm_enabled=bool(bgm_enabled),
            sfx_enabled=bool(sfx_enabled),
            debug_party=bool(debug_party),
            debug_collision=bool(debug_coll),
            enemy_spawn_global_interval=float(global_interval),
            font_sizes=dict(font_sizes),
        )
