# engine/core/config/engine_settings.py

from dataclasses import dataclass
from pathlib import Path
import yaml

SETTINGS_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


@dataclass(frozen=True)
class EngineSettings:
    saves_dir:                 str
    text_speed:                str
    smooth_collision:          bool
    mc_exchange_confirm_large: bool
    use_aoe_confirm:           bool
    debug_party:               bool
    debug_items:               bool

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "EngineSettings":
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        saves_dir     = (data.get("saves")    or {}).get("dir")
        text_speed    = (data.get("dialogue") or {}).get("text_speed")
        smooth        = (data.get("movement") or {}).get("smooth_collision", True)
        confirm_large = (data.get("shop")     or {}).get("mc_exchange_confirm_large", True)
        use_aoe       = (data.get("item")     or {}).get("use_aoe_confirm", True)
        debug_party   = (data.get("debug")    or {}).get("party", False)
        debug_items   = (data.get("debug")    or {}).get("items", False)

        missing = []
        if saves_dir is None:
            missing.append("saves.dir")
        if text_speed is None:
            missing.append("dialogue.text_speed")
        if missing:
            raise KeyError(
                f"Missing required settings in {path}: {', '.join(missing)}"
            )

        return cls(
            saves_dir=saves_dir,
            text_speed=text_speed,
            smooth_collision=bool(smooth),
            mc_exchange_confirm_large=bool(confirm_large),
            use_aoe_confirm=bool(use_aoe),
            debug_party=bool(debug_party),
            debug_items=bool(debug_items),
        )
