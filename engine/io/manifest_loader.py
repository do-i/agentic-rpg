# engine/io/manifest_loader.py

from pathlib import Path

from engine.io.yaml_loader import load_yaml_required


class ManifestLoader:
    def __init__(self, scenario_path: str) -> None:
        self._scenario_path = Path(scenario_path)

    def load(self) -> dict:
        return load_yaml_required(self._scenario_path / "manifest.yaml")

    @property
    def scenario_path(self) -> Path:
        return self._scenario_path