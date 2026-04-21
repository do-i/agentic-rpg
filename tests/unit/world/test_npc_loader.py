# tests/unit/world/test_npc_loader.py

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from engine.world.npc_loader import NpcLoader
from engine.world.npc import Npc
from engine.world.sprite_sheet import Direction
from engine.util.pseudo_random import PseudoRandom


TS = 32
_rng = PseudoRandom(seed=0)


@pytest.fixture
def loader() -> NpcLoader:
    return NpcLoader(tile_size=TS, rng=_rng)


@pytest.fixture
def loader_with_path(tmp_path) -> NpcLoader:
    return NpcLoader(tile_size=TS, scenario_path=tmp_path, rng=_rng)


def write_map(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "map.yaml"
    with open(p, "w") as f:
        yaml.dump(data, f)
    return p


# ── load_from_map ─────────────────────────────────────────────

class TestNpcLoader:
    def test_empty_file_returns_empty_list(self, loader, tmp_path):
        p = write_map(tmp_path, {})
        assert loader.load_from_map(p) == []

    def test_missing_file_returns_empty_list(self, loader, tmp_path):
        assert loader.load_from_map(tmp_path / "nonexistent.yaml") == []

    def test_loads_basic_npc(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "elder", "dialogue": "elder_intro", "position": [12, 8]}]
        })
        npcs = loader.load_from_map(p)
        assert len(npcs) == 1
        assert npcs[0].id == "elder"
        assert npcs[0].dialogue_id == "elder_intro"

    def test_loads_multiple_npcs(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [
                {"id": "npc_a", "dialogue": "dlg_a", "position": [1, 1]},
                {"id": "npc_b", "dialogue": "dlg_b", "position": [2, 2]},
            ]
        })
        npcs = loader.load_from_map(p)
        assert len(npcs) == 2

    def test_npc_with_present_conditions(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{
                "id": "gate",
                "dialogue": "gate_dlg",
                "position": [5, 5],
                "present": {
                    "requires": ["flag_a"],
                    "excludes": ["flag_b"],
                }
            }]
        })
        from engine.common.flag_state import FlagState
        npcs = loader.load_from_map(p)
        npc = npcs[0]
        assert npc.is_present(FlagState({"flag_a"}))
        assert not npc.is_present(FlagState({"flag_a", "flag_b"}))
        assert not npc.is_present(FlagState())

    def test_npc_position_translated_to_pixels(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "n", "dialogue": "d", "position": [3, 7]}]
        })
        npcs = loader.load_from_map(p)
        pos = npcs[0].pixel_position
        assert pos.x == 3 * TS
        assert pos.y == 7 * TS

    def test_default_facing_loaded(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "n", "dialogue": "d", "position": [1, 1], "default_facing": "left"}]
        })
        npcs = loader.load_from_map(p)
        assert npcs[0]._default_facing == Direction.LEFT

    def test_default_facing_defaults_to_down(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "n", "dialogue": "d", "position": [1, 1]}]
        })
        npcs = loader.load_from_map(p)
        assert npcs[0]._default_facing == Direction.DOWN

    def test_no_sprite_gives_none(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "n", "dialogue": "d", "position": [1, 1]}]
        })
        npcs = loader.load_from_map(p)
        assert npcs[0]._sprite_sheet is None

    def test_sprite_path_missing_logs_warn(self, loader_with_path, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "n", "dialogue": "d", "position": [1, 1],
                      "sprite": "assets/sprites/npc/nonexistent.tsx"}]
        })
        # missing sprite → no crash, no sprite loaded
        npcs = loader_with_path.load_from_map(p)
        assert npcs[0]._sprite_sheet is None

    def test_no_scenario_path_skips_sprite(self, loader, tmp_path):
        p = write_map(tmp_path, {
            "npcs": [{"id": "n", "dialogue": "d", "position": [1, 1],
                      "sprite": "assets/sprites/npc/man_01.tsx"}]
        })
        npcs = loader.load_from_map(p)
        assert npcs[0]._sprite_sheet is None

    def test_missing_id_raises(self, loader, tmp_path):
        p = write_map(tmp_path, {"npcs": [{"position": [1, 1]}]})
        with pytest.raises(KeyError, match="id"):
            loader.load_from_map(p)

    def test_missing_position_raises(self, loader, tmp_path):
        p = write_map(tmp_path, {"npcs": [{"id": "n"}]})
        with pytest.raises(KeyError, match="position"):
            loader.load_from_map(p)
