from __future__ import annotations

from unittest.mock import MagicMock, patch

from engine.world.world_map_scene import WorldMapScene


def _scene_for_battle_launch() -> WorldMapScene:
    scene = WorldMapScene.__new__(WorldMapScene)
    scene._holder = MagicMock()
    scene._player = MagicMock()
    scene._encounter_manager = MagicMock()
    scene._encounter_resolver = MagicMock()
    scene._scene_manager = MagicMock()
    scene._registry = MagicMock()
    scene._loader = MagicMock()
    scene._game_state_manager = MagicMock()
    scene._effect_handler = MagicMock()
    scene._bgm_manager = MagicMock()
    scene._sfx_manager = MagicMock()
    scene._rng = MagicMock()
    scene._balance = MagicMock()
    scene._screen_width = 1280
    scene._screen_height = 766
    scene._engaged_enemy = None
    return scene


def test_launch_battle_marks_enemy_engaged_only_when_launch_succeeds():
    scene = _scene_for_battle_launch()
    enemy = MagicMock()

    with patch("engine.world.world_map_scene.launch_battle_from_enemy", return_value=True):
        assert scene._launch_battle_from_enemy(enemy) is True

    assert scene._engaged_enemy is enemy


def test_launch_battle_leaves_enemy_unengaged_when_launch_fails():
    scene = _scene_for_battle_launch()
    enemy = MagicMock()

    with patch("engine.world.world_map_scene.launch_battle_from_enemy", return_value=False):
        assert scene._launch_battle_from_enemy(enemy) is False

    assert scene._engaged_enemy is None
