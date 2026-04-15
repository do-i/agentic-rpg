# tests/unit/core/battle/test_enemy_loader.py

import pytest
import yaml
from pathlib import Path

from engine.battle.enemy_loader import EnemyLoader


GOBLIN_DOC = {
    "id": "goblin",
    "name": "Goblin",
    "hp": 20,
    "atk": 8,
    "def": 3,
    "mres": 2,
    "dex": 10,
    "exp": 5,
    "boss": False,
    "sprite_scale": 100,
    "drops": {"loot": [{"item": "potion", "weight": 10}]},
    "ai": {"attack_weight": 1.0},
    "targeting": {"prefer": "lowest_hp"},
}

BAT_DOC = {
    "id": "bat",
    "name": "Bat",
    "hp": 10,
    "atk": 5,
    "def": 1,
    "mres": 1,
    "dex": 14,
    "exp": 3,
}


@pytest.fixture
def enemies_dir(tmp_path):
    d = tmp_path / "enemies"
    d.mkdir()
    # Multi-doc YAML in a single rank file
    content = yaml.dump(GOBLIN_DOC) + "---\n" + yaml.dump(BAT_DOC)
    (d / "enemies_rank_1_SS.yaml").write_text(content)
    return d


@pytest.fixture
def loader(enemies_dir):
    return EnemyLoader(enemies_dir)


# ── Index building ────────────────────────────────────────────

class TestBuildIndex:
    def test_indexes_all_enemies_in_file(self, loader):
        assert "goblin" in loader.known_ids
        assert "bat" in loader.known_ids

    def test_empty_dir_has_no_ids(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert EnemyLoader(empty).known_ids == []

    def test_nonexistent_dir_has_no_ids(self, tmp_path):
        assert EnemyLoader(tmp_path / "missing").known_ids == []


# ── load ──────────────────────────────────────────────────────

class TestLoad:
    def test_returns_combatant_for_known_id(self, loader):
        c = loader.load("goblin")
        assert c is not None
        assert c.name == "Goblin"
        assert c.hp == 20
        assert c.hp_max == 20
        assert c.is_enemy

    def test_returns_none_for_unknown_id(self, loader):
        assert loader.load("dragon") is None

    def test_stats_mapped_correctly(self, loader):
        c = loader.load("goblin")
        assert c.atk == 8
        assert c.def_ == 3
        assert c.dex == 10
        assert c.exp_yield == 5

    def test_mp_always_zero(self, loader):
        c = loader.load("goblin")
        assert c.mp == 0
        assert c.mp_max == 0

    def test_second_doc_in_file(self, loader):
        c = loader.load("bat")
        assert c is not None
        assert c.name == "Bat"


# ── _build defaults ───────────────────────────────────────────

class TestBuildDefaults:
    def test_minimal_enemy_uses_defaults(self, tmp_path):
        d = tmp_path / "e"
        d.mkdir()
        (d / "enemies_rank_1_SS.yaml").write_text("id: minimal\n")
        loader = EnemyLoader(d)
        c = loader.load("minimal")
        assert c.name == "minimal"
        assert c.hp == 10
        assert c.atk == 5
        assert c.exp_yield == 0


# ── AI loading ────────────────────────────────────────────────

class TestAiLoading:
    def test_inline_ai_is_loaded(self, loader):
        c = loader.load("goblin")
        assert c.ai_data["ai"]["attack_weight"] == 1.0
        assert c.ai_data["targeting"]["prefer"] == "lowest_hp"

    def test_ai_ref_loads_external_file(self, tmp_path):
        d = tmp_path / "enemies"
        d.mkdir()
        ai_content = {
            "ai": {"attack_weight": 0.7},
            "targeting": {"prefer": "random"},
        }
        (d / "boss_ai.yaml").write_text(yaml.dump(ai_content))
        enemy_doc = {
            "id": "spider_boss",
            "name": "Spider Boss",
            "hp": 100,
            "ai_ref": "boss_ai.yaml",
        }
        (d / "enemies_rank_8_F.yaml").write_text(yaml.dump(enemy_doc))

        loader = EnemyLoader(d)
        c = loader.load("spider_boss")
        assert c.ai_data["ai"]["attack_weight"] == 0.7
        assert c.ai_data["targeting"]["prefer"] == "random"

    def test_missing_ai_ref_falls_back_to_inline(self, tmp_path):
        d = tmp_path / "enemies"
        d.mkdir()
        enemy_doc = {
            "id": "ghost",
            "hp": 30,
            "ai_ref": "nonexistent_ai.yaml",
            "ai": {"attack_weight": 0.5},
        }
        (d / "enemies_rank_1_SS.yaml").write_text(yaml.dump(enemy_doc))

        loader = EnemyLoader(d)
        c = loader.load("ghost")
        # Falls back to inline ai block
        assert c.ai_data["ai"]["attack_weight"] == 0.5
