# tests/unit/world/test_item_box_loader.py

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from engine.world.item_box_loader import ItemBoxLoader

TS = 32


def make_loader(tmp_path: Path, manifest_data: dict | None = None) -> ItemBoxLoader:
    """Build an ItemBoxLoader with a fake manifest loader; no sprite loaded."""
    manifest = manifest_data if manifest_data is not None else {}
    fake_loader = MagicMock()
    fake_loader.scenario_path = tmp_path
    fake_loader.load.return_value = manifest
    return ItemBoxLoader(manifest_loader=fake_loader, tile_size=TS)


def write_map(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "map.yaml"
    with open(p, "w") as f:
        yaml.dump(data, f)
    return p


class TestLoadFromMap:
    def test_empty_file_returns_empty_list(self, tmp_path):
        loader = make_loader(tmp_path)
        p = write_map(tmp_path, {})
        assert loader.load_from_map(p) == []

    def test_missing_file_returns_empty_list(self, tmp_path):
        loader = make_loader(tmp_path)
        assert loader.load_from_map(tmp_path / "nonexistent.yaml") == []

    def test_loads_basic_box(self, tmp_path):
        loader = make_loader(tmp_path)
        p = write_map(tmp_path, {
            "item_boxes": [{
                "id": "chest_a",
                "position": [3, 7],
                "loot": {"items": [{"id": "potion", "qty": 2}]},
            }]
        })
        boxes = loader.load_from_map(p)
        assert len(boxes) == 1
        assert boxes[0].id == "chest_a"
        assert boxes[0].loot_items == [("potion", 2)]
        assert boxes[0].loot_magic_cores == []

    def test_magic_cores_mapped_to_mc_ids(self, tmp_path):
        loader = make_loader(tmp_path)
        p = write_map(tmp_path, {
            "item_boxes": [{
                "id": "chest_b",
                "position": [1, 1],
                "loot": {"magic_cores": [
                    {"size": "m", "qty": 3},
                    {"size": "xl", "qty": 1},
                ]}
            }]
        })
        boxes = loader.load_from_map(p)
        assert boxes[0].loot_magic_cores == [("mc_m", 3), ("mc_xl", 1)]

    def test_optional_sections_default_to_empty(self, tmp_path):
        loader = make_loader(tmp_path)
        p = write_map(tmp_path, {
            "item_boxes": [{"id": "c", "position": [0, 0], "loot": {}}]
        })
        boxes = loader.load_from_map(p)
        assert boxes[0].loot_items == []
        assert boxes[0].loot_magic_cores == []

    def test_invalid_magic_core_size_raises(self, tmp_path):
        loader = make_loader(tmp_path)
        p = write_map(tmp_path, {
            "item_boxes": [{
                "id": "bad",
                "position": [0, 0],
                "loot": {"magic_cores": [{"size": "jumbo", "qty": 1}]}
            }]
        })
        with pytest.raises(ValueError, match="invalid magic-core size"):
            loader.load_from_map(p)

    def test_present_conditions_applied(self, tmp_path):
        loader = make_loader(tmp_path)
        p = write_map(tmp_path, {
            "item_boxes": [{
                "id": "gated",
                "position": [0, 0],
                "present": {"requires": ["quest_a"], "excludes": ["looted"]},
                "loot": {"items": [{"id": "potion", "qty": 1}]},
            }]
        })
        from engine.common.flag_state import FlagState
        box = loader.load_from_map(p)[0]
        assert box.is_present(FlagState({"quest_a"}))
        assert not box.is_present(FlagState({"quest_a", "looted"}))
        assert not box.is_present(FlagState())

    def test_no_manifest_sprite_leaves_sprite_none(self, tmp_path):
        loader = make_loader(tmp_path, manifest_data={})
        p = write_map(tmp_path, {
            "item_boxes": [{"id": "c", "position": [0, 0], "loot": {}}]
        })
        box = loader.load_from_map(p)[0]
        assert box._sprite is None
