# engine/core/config/engine_settings.py

from dataclasses import dataclass
from pathlib import Path
import yaml

SETTINGS_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


@dataclass(frozen=True)
class EngineSettings:
    saves_dir:        str
    text_speed:       str
    smooth_collision: bool   # axis-separation sliding on walls and NPCs
    debug_party:      bool   # add all party members at new game start

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "EngineSettings":
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        saves_dir   = (data.get("saves")    or {}).get("dir")
        text_speed  = (data.get("dialogue") or {}).get("text_speed")
        smooth      = (data.get("movement") or {}).get("smooth_collision", True)
        debug_party = (data.get("debug")    or {}).get("party", False)

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
            debug_party=bool(debug_party),
        )
