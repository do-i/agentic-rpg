# tests/unit/core/scenes/test_world_map_logic_loader.py

import yaml
from pathlib import Path

from engine.world.world_map_logic import load_magic_cores


class TestLoadMagicCores:
    def test_loads_and_sorts_by_rate_descending(self, tmp_path):
        items_dir = tmp_path / "data" / "items"
        items_dir.mkdir(parents=True)
        data = [
            {"id": "mc_xs", "name": "XS", "exchange_rate": 1},
            {"id": "mc_xl", "name": "XL", "exchange_rate": 10_000},
            {"id": "mc_m",  "name": "M",  "exchange_rate": 100},
        ]
        (items_dir / "magic_cores.yaml").write_text(yaml.dump(data))

        result = load_magic_cores(tmp_path)
        assert [r["id"] for r in result] == ["mc_xl", "mc_m", "mc_xs"]

    def test_returns_empty_when_file_missing(self, tmp_path):
        assert load_magic_cores(tmp_path) == []

    def test_returns_empty_for_empty_file(self, tmp_path):
        items_dir = tmp_path / "data" / "items"
        items_dir.mkdir(parents=True)
        (items_dir / "magic_cores.yaml").write_text("")

        assert load_magic_cores(tmp_path) == []
