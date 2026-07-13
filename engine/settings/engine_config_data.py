# engine/settings/engine_config_data.py

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import yaml

from engine.io.yaml_loader import SafeLoader


SETTINGS_PATH = Path(__file__).parent / "settings.yaml"

_REQUIRED_FONT_SIZES = ("small", "medium", "large", "xlarge")

# (dotted yaml path, constructor attribute, cast)
_FIELD_SPEC: tuple[tuple[str, str, Callable[[Any], Any]], ...] = (
    ("display.screen_width",           "screen_width",                int),
    ("display.screen_height",          "screen_height",               int),
    ("display.fps",                    "fps",                         int),
    ("display.window_position",        "window_position",             str),
    ("tiles.tile_size",                "tile_size",                   int),
    ("saves.dir",                      "saves_dir",                   str),
    ("dialogue.text_speed",            "text_speed",                  str),
    ("movement.smooth_collision",      "smooth_collision",            bool),
    ("shop.mc_exchange_confirm_large", "mc_exchange_confirm_large",   bool),
    ("item.use_aoe_confirm",           "use_aoe_confirm",             bool),
    ("audio.bgm_enabled",              "bgm_enabled",                 bool),
    ("audio.sfx_enabled",              "sfx_enabled",                 bool),
    ("enemy_spawn.global_interval",    "enemy_spawn_global_interval", float),
)


def _dig(data: Any, dotted: str) -> Any:
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


@dataclass(frozen=True)
class EngineConfigData:
    # display
    screen_width:    int
    screen_height:   int
    fps:             int
    window_position: str
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
            data = yaml.load(f, Loader=SafeLoader) or {}

        values: dict[str, Any] = {}
        missing: list[str] = []
        for dotted, attr, cast in _FIELD_SPEC:
            raw = _dig(data, dotted)
            if raw is None:
                missing.append(dotted)
            else:
                values[attr] = cast(raw)

        font_sizes = _dig(data, "fonts.sizes") or {}
        missing += [
            f"fonts.sizes.{k}" for k in _REQUIRED_FONT_SIZES if k not in font_sizes
        ]

        if missing:
            raise KeyError(
                f"Missing required settings in {path}: {', '.join(missing)} "
                f"(e.g. add 'screen_width: 1280' under 'display:')"
            )

        # The debug block is deliberately optional (dev tooling): absent → off.
        debug_cfg = data.get("debug") or {}
        values["debug_party"] = bool(debug_cfg.get("party"))
        values["debug_collision"] = bool(debug_cfg.get("collision"))
        values["font_sizes"] = dict(font_sizes)
        return cls(**values)
