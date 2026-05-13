from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ScenarioMaps:
    scenario_root: Path
    maps_dir: Path
    data_maps_dir: Path
    tmx_paths: list[Path]

    def yaml_for(self, tmx_path: Path) -> Path | None:
        """Return the map-data YAML matching a TMX file, or None if absent."""
        candidate = self.data_maps_dir / f"{tmx_path.stem}.yaml"
        return candidate if candidate.is_file() else None


def load_scenario_maps(scenario_root: Path) -> ScenarioMaps:
    manifest_path = scenario_root / "manifest.yaml"
    if not manifest_path.is_file():
        raise ValueError(
            f"Scenario manifest not found: {manifest_path}. "
            f"Expected a 'manifest.yaml' file at the scenario root "
            f"(example: rusted_kingdoms/manifest.yaml)."
        )

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    refs = manifest.get("refs")
    if not isinstance(refs, dict) or "maps" not in refs:
        raise ValueError(
            f"Manifest {manifest_path} is missing required property 'refs.maps' "
            f"(example: refs:\\n  maps: data/maps/)."
        )

    maps_rel = refs["maps"]
    data_maps_dir = (scenario_root / maps_rel).resolve()

    assets_maps_dir = (scenario_root / "assets" / "maps").resolve()
    tmx_dir = assets_maps_dir if assets_maps_dir.is_dir() else data_maps_dir
    if not tmx_dir.is_dir():
        raise ValueError(
            f"Map directory not found: tried {assets_maps_dir} and {data_maps_dir}. "
            f"Expected one of them to contain .tmx files."
        )

    tmx_paths = sorted(tmx_dir.glob("*.tmx"))
    return ScenarioMaps(
        scenario_root=scenario_root.resolve(),
        maps_dir=tmx_dir,
        data_maps_dir=data_maps_dir,
        tmx_paths=tmx_paths,
    )
