# engine/data/loader.py

from pathlib import Path
import yaml


class ManifestLoader:
    def __init__(self, scenario_path: str) -> None:
        self._scenario_path = Path(scenario_path)

    def load(self) -> dict:
        manifest_path = self._scenario_path / "manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.yaml not found at {manifest_path}")
        with open(manifest_path, "r") as f:
            return yaml.safe_load(f)

    @property
    def scenario_path(self) -> Path:
        return self._scenario_path