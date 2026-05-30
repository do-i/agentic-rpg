from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from engine.encounter.encounter_zone_data import (
    BossConfig,
    EncounterSet,
    EncounterZone,
    Formation,
)
from engine.util.pseudo_random import PseudoRandom
from engine.world.world_map_init import _build_spawner


def _zone(*, with_boss: bool = True) -> EncounterZone:
    return EncounterZone(
        zone_id="zone_boss",
        name="Boss Zone",
        density=1.0,
        entries=EncounterSet([Formation(["goblin"], weight=1)]),
        boss=BossConfig("boss_enemy", "Boss Enemy", flag_set="boss_defeated")
        if with_boss
        else None,
    )


def _tile_map(*, spawn_tiles: list[dict] | None = None, boss_spawn: dict | None = None):
    tile_map = MagicMock()
    tile_map.enemy_spawn_tiles = spawn_tiles or []
    tile_map.boss_spawn_tile = boss_spawn
    return tile_map


def _manager(zone: EncounterZone | None):
    manager = MagicMock()
    manager.get_zone.return_value = zone
    return manager


def test_build_spawner_allows_boss_only_map_without_regular_spawn_tiles():
    spawner = _build_spawner(
        tile_map=_tile_map(boss_spawn={"x": 64, "y": 96, "is_boss": True}),
        map_data={},
        encounter_manager=_manager(_zone(with_boss=True)),
        encounter_resolver=MagicMock(),
        scenario_path=Path("/fake"),
        rng=PseudoRandom(seed=0),
        sprite_cache=MagicMock(),
        tile_size=32,
        balance=None,
        global_interval=30.0,
    )

    assert spawner is not None
    assert spawner._spawn_tiles == []
    assert spawner._boss_tile == {"x": 64, "y": 96, "is_boss": True}


def test_build_spawner_still_skips_maps_without_regular_or_boss_spawns():
    spawner = _build_spawner(
        tile_map=_tile_map(),
        map_data={},
        encounter_manager=_manager(_zone(with_boss=True)),
        encounter_resolver=MagicMock(),
        scenario_path=Path("/fake"),
        rng=PseudoRandom(seed=0),
        sprite_cache=MagicMock(),
        tile_size=32,
        balance=None,
        global_interval=30.0,
    )

    assert spawner is None
