# tests/unit/battle/test_battle_asset_cache.py
#
# Enemy sheet resolution in BattleAssetCache: pre-rendered battle sheets
# (<id>_battle.tsx) take priority over world-map sheets, and larger battle
# frames are smoothly downscaled to the enemy rect.

from __future__ import annotations

from pathlib import Path

import pygame
import pytest

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.combatant import Combatant


@pytest.fixture(autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def write_sheet(sprites_dir: Path, name: str, tile: int, color) -> None:
    """Write a 9x12 sheet of solid-color tiles plus its TSX."""
    cols, rows = 9, 12
    surf = pygame.Surface((cols * tile, rows * tile), pygame.SRCALPHA)
    surf.fill(color)
    pygame.image.save(surf, str(sprites_dir / f"{name}.png"))
    (sprites_dir / f"{name}.tsx").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<tileset version="1.10" name="{name}" tilewidth="{tile}" tileheight="{tile}" '
        f'tilecount="{cols * rows}" columns="{cols}">\n'
        f' <image source="{name}.png" width="{cols * tile}" height="{rows * tile}"/>\n'
        "</tileset>\n"
    )


@pytest.fixture
def scenario(tmp_path):
    sprites_dir = tmp_path / "assets" / "sprites" / "enemies"
    sprites_dir.mkdir(parents=True)
    return tmp_path


def make_enemy(enemy_id: str = "slime") -> Combatant:
    return Combatant(
        id=enemy_id, name="Slime", hp=1, hp_max=1, mp=0, mp_max=0,
        atk=1, def_=1, mres=1, dex=1, is_enemy=True,
    )


class TestBattleSheetPreference:
    def test_prefers_battle_sheet_when_present(self, scenario):
        sprites_dir = scenario / "assets" / "sprites" / "enemies"
        write_sheet(sprites_dir, "slime", 64, (255, 0, 0, 255))
        write_sheet(sprites_dir, "slime_battle", 256, (0, 255, 0, 255))

        cache = BattleAssetCache(scenario)
        sheet = cache._load_enemy_sheet("slime")
        assert sheet is not None
        assert sheet.tsx_path.name == "slime_battle.tsx"
        assert sheet.frame_size == (256, 256)

    def test_falls_back_to_map_sheet(self, scenario):
        sprites_dir = scenario / "assets" / "sprites" / "enemies"
        write_sheet(sprites_dir, "slime", 64, (255, 0, 0, 255))

        cache = BattleAssetCache(scenario)
        sheet = cache._load_enemy_sheet("slime")
        assert sheet is not None
        assert sheet.tsx_path.name == "slime.tsx"

    def test_missing_sheets_return_none(self, scenario):
        cache = BattleAssetCache(scenario)
        assert cache._load_enemy_sheet("slime") is None


class TestSpriteScaling:
    def test_idle_sprite_scaled_to_enemy_rect(self, scenario):
        sprites_dir = scenario / "assets" / "sprites" / "enemies"
        write_sheet(sprites_dir, "slime_battle", 256, (0, 255, 0, 255))

        cache = BattleAssetCache(scenario)
        enemy = make_enemy()
        sprite = cache.load_enemy_sprite(enemy)
        assert sprite is not None
        assert sprite.get_size() == cache.enemy_rect_size(enemy)

    def test_attack_frames_scaled_to_enemy_rect(self, scenario):
        sprites_dir = scenario / "assets" / "sprites" / "enemies"
        write_sheet(sprites_dir, "slime_battle", 256, (0, 255, 0, 255))

        cache = BattleAssetCache(scenario)
        enemy = make_enemy()
        frames = cache.load_enemy_attack_frames(enemy, row_offset=4, frame_count=5)
        assert len(frames) == 5
        assert all(f.get_size() == cache.enemy_rect_size(enemy) for f in frames)
