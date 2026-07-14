# tests/unit/core/state/test_manifest_loader.py

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from engine.io.manifest_loader import ManifestLoader


@pytest.fixture
def scenario_dir(tmp_path: Path) -> Path:
    return tmp_path


def write_manifest(scenario_dir: Path, data: dict) -> Path:
    p = scenario_dir / "manifest.yaml"
    p.write_text(yaml.dump(data))
    return p


# ── load ──────────────────────────────────────────────────────

class TestLoad:
    def test_returns_parsed_dict(self, scenario_dir):
        manifest = {
            "protagonist": {"id": "aric", "name": "Aric"},
            "start": {"map": "town_01", "position": [4, 5]},
            "bootstrap_flags": ["story_started"],
        }
        write_manifest(scenario_dir, manifest)
        loader = ManifestLoader(str(scenario_dir))
        assert loader.load() == manifest

    def test_missing_manifest_raises(self, scenario_dir):
        loader = ManifestLoader(str(scenario_dir))
        with pytest.raises(FileNotFoundError) as ei:
            loader.load()
        # Error message includes the missing path so the user can find it.
        assert "manifest.yaml" in str(ei.value)

    def test_empty_manifest_returns_none(self, scenario_dir):
        (scenario_dir / "manifest.yaml").write_text("")
        loader = ManifestLoader(str(scenario_dir))
        assert loader.load() is None

    def test_invalid_yaml_raises(self, scenario_dir):
        (scenario_dir / "manifest.yaml").write_text(":\n bad:\n :")
        loader = ManifestLoader(str(scenario_dir))
        with pytest.raises(yaml.YAMLError):
            loader.load()


# ── scenario_path property ────────────────────────────────────

class TestScenarioPath:
    def test_exposes_path_object(self, scenario_dir):
        loader = ManifestLoader(str(scenario_dir))
        assert isinstance(loader.scenario_path, Path)
        assert loader.scenario_path == scenario_dir

    def test_path_is_absolute_when_input_is_absolute(self, scenario_dir):
        loader = ManifestLoader(str(scenario_dir.resolve()))
        assert loader.scenario_path.is_absolute()
