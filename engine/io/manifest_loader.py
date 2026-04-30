# engine/io/manifest_loader.py

from __future__ import annotations

from pathlib import Path

from engine.io.yaml_loader import load_yaml_required_cached


class ManifestLoader:
    def __init__(self, scenario_path: str) -> None:
        self._scenario_path = Path(scenario_path)

    def load(self) -> dict:
        return load_yaml_required_cached(self._scenario_path / "manifest.yaml")

    @property
    def scenario_path(self) -> Path:
        return self._scenario_path