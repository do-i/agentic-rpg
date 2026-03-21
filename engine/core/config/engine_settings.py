# engine/core/config/engine_settings.py

from dataclasses import dataclass
from pathlib import Path
import yaml

SETTINGS_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


@dataclass(frozen=True)
class EngineSettings:
    saves_dir: str
    text_speed: str

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "EngineSettings":
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        saves_dir = (data.get("saves") or {}).get("dir")
        text_speed = (data.get("dialogue") or {}).get("text_speed")

        missing = []
        if saves_dir is None:
            missing.append("saves.dir")
        if text_speed is None:
            missing.append("dialogue.text_speed")
        if missing:
            raise KeyError(
                f"Missing required settings in {path}: {', '.join(missing)}"
            )

        return cls(saves_dir=saves_dir, text_speed=text_speed)
