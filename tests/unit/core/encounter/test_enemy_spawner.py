# tests/unit/core/encounter/test_enemy_spawner.py

import pytest
import time
from unittest.mock import MagicMock, patch
from pathlib import Path

from engine.encounter.enemy_spawner import (
    EnemySpawner,
    ROGUE_CHASE_REDUCTION,
    STEALTH_CLOAK_REDUCTION,
    LURE_CHARM_INTERVAL_MULT,
)
from engine.encounter.encounter_zone_data import (
    EncounterZone, EncounterSet, Formation, BossConfig,
)
from engine.encounter.enemy_sprite import EnemySprite


def make_zone(density=0.8, with_boss=False, spawn_frequency=None) -> EncounterZone:
    set_a = EncounterSet([Formation(["goblin"], 100, chase_range=3)])
    set_b = EncounterSet([Formation(["bat"], 100, chase_range=2)])
    boss = BossConfig("spider_boss", "Boss Spider", once=True,
                      flag_set="boss_defeated") if with_boss else None
    return EncounterZone(
        zone_id="zone_01", name="Forest", density=density,
        set_a=set_a, set_b=set_b, boss=boss,
        spawn_frequency=spawn_frequency,
    )


def make_spawn_tiles(count=3) -> list[dict]:
    return [{"x": i * 96, "y": i * 96, "is_boss": False} for i in range(count)]


def make_spawner(
    zone=None,
    spawn_tiles=None,
    init_count=2,
    max_count=4,
    map_interval=None,
    global_interval=30.0,
) -> EnemySpawner:
    if zone is None:
        zone = make_zone()
    if spawn_tiles is None:
        spawn_tiles = make_spawn_tiles(4)

    resolver = MagicMock()
    resolver.pick_formation.return_value = Formation(["goblin"], 100, chase_range=3)

    return EnemySpawner(
        zone=zone,
        spawn_tiles=spawn_tiles,
        init_count=init_count,
        max_count=max_count,
        map_interval=map_interval,
        global_interval=global_interval,
        resolver=resolver,
        scenario_path=Path("/fake"),
        tile_size=32,
    )


# ── Interval resolution ───────────────────────────────────────

class TestIntervalResolution:
    def test_map_interval_takes_priority(self):
        zone = make_zone(spawn_frequency=20.0)
        spawner = make_spawner(zone=zone, map_interval=10.0, global_interval=30.0)
        assert spawner._base_interval == 10.0

    def test_zone_frequency_overrides_global(self):
        zone = make_zone(spawn_frequency=20.0)
        spawner = make_spawner(zone=zone, map_interval=None, global_interval=30.0)
        assert spawner._base_interval == 20.0

    def test_global_interval_used_as_fallback(self):
        zone = make_zone(spawn_frequency=None)
        spawner = make_spawner(zone=zone, map_interval=None, global_interval=30.0)
        assert spawner._base_interval == 30.0


# ── init_spawn ────────────────────────────────────────────────

class TestInitSpawn:
    def test_spawns_init_count_enemies(self):
        spawner = make_spawner(init_count=3, max_count=6)
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        assert len(spawner._active) == 3

    def test_does_not_exceed_max_count(self):
        spawner = make_spawner(init_count=10, max_count=3)
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        assert len(spawner._active) <= 3

    def test_spawns_boss_when_not_defeated(self):
        zone = make_zone(with_boss=True)
        tiles = make_spawn_tiles(4)
        tiles.append({"x": 500, "y": 500, "is_boss": True})
        spawner = make_spawner(zone=zone, spawn_tiles=tiles, init_count=0)
        flags = MagicMock()
        flags.has_flag.return_value = False   # boss not defeated
        spawner.init_spawn(flags)
        bosses = [e for e in spawner._active if e.is_boss]
        assert len(bosses) == 1

    def test_skips_boss_when_defeated(self):
        zone = make_zone(with_boss=True)
        tiles = make_spawn_tiles(4)
        tiles.append({"x": 500, "y": 500, "is_boss": True})
        spawner = make_spawner(zone=zone, spawn_tiles=tiles, init_count=0)
        flags = MagicMock()
        flags.has_flag.return_value = True   # boss already defeated
        spawner.init_spawn(flags)
        bosses = [e for e in spawner._active if e.is_boss]
        assert len(bosses) == 0


# ── on_enemy_defeated / respawn queue ─────────────────────────

class TestOnEnemyDefeated:
    def test_removes_enemy_from_active(self):
        spawner = make_spawner(init_count=2)
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        enemy = spawner._active[0]
        spawner.on_enemy_defeated(enemy)
        assert enemy not in spawner._active

    def test_adds_to_respawn_queue(self):
        spawner = make_spawner(init_count=1)
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        enemy = spawner._active[0]
        spawner.on_enemy_defeated(enemy)
        assert len(spawner._respawn_queue) == 1

    def test_respawns_after_interval(self):
        spawner = make_spawner(init_count=0, max_count=5, global_interval=1.0)
        # Manually add a defeated enemy
        formation = Formation(["goblin"], 100, chase_range=3)
        past_time = time.monotonic() - 5.0   # 5 seconds ago
        spawner._respawn_queue.append((formation, False, past_time))

        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        party = MagicMock()
        party.members = []

        spawner.update(0.016, 0.0, 0.0, collision, party)
        # Interval elapsed, enemy should have spawned
        assert len(spawner._active) == 1
        assert len(spawner._respawn_queue) == 0


# ── check_player_collision ────────────────────────────────────

class TestCheckPlayerCollision:
    def test_returns_none_when_no_enemies(self):
        spawner = make_spawner(init_count=0)
        result = spawner.check_player_collision((0, 0, 10, 10))
        assert result is None

    def test_returns_enemy_on_overlap(self):
        spawner = make_spawner(init_count=0)
        enemy = MagicMock(spec=EnemySprite)
        enemy.collides_with.return_value = True
        spawner._active.append(enemy)
        result = spawner.check_player_collision((0, 0, 20, 18))
        assert result is enemy

    def test_returns_none_when_no_overlap(self):
        spawner = make_spawner(init_count=0)
        enemy = MagicMock(spec=EnemySprite)
        enemy.collides_with.return_value = False
        spawner._active.append(enemy)
        result = spawner.check_player_collision((9999, 9999, 20, 18))
        assert result is None


# ── Modifier computation ──────────────────────────────────────

class TestComputeModifiers:
    def _make_party(self, class_name, accessory=""):
        member = MagicMock()
        member.class_name = class_name
        member.equipped = {"accessory": accessory}
        party = MagicMock()
        party.members = [member]
        return party

    def test_no_modifiers_for_non_rogue(self):
        spawner = make_spawner()
        party = self._make_party("warrior")
        mult, reduction = spawner._compute_modifiers(party)
        assert mult == 1.0
        assert reduction == 0

    def test_rogue_reduces_chase_range(self):
        spawner = make_spawner()
        party = self._make_party("rogue")
        _, reduction = spawner._compute_modifiers(party)
        assert reduction == ROGUE_CHASE_REDUCTION

    def test_stealth_cloak_adds_reduction(self):
        spawner = make_spawner()
        party = self._make_party("rogue", accessory="stealth_cloak")
        _, reduction = spawner._compute_modifiers(party)
        assert reduction == ROGUE_CHASE_REDUCTION + STEALTH_CLOAK_REDUCTION

    def test_lure_charm_speeds_up_spawns(self):
        spawner = make_spawner()
        party = self._make_party("rogue", accessory="lure_charm")
        mult, _ = spawner._compute_modifiers(party)
        assert mult == LURE_CHARM_INTERVAL_MULT

    def test_none_party_returns_defaults(self):
        spawner = make_spawner()
        mult, reduction = spawner._compute_modifiers(None)
        assert mult == 1.0
        assert reduction == 0


# ── Occupied tile detection ───────────────────────────────────

class TestTileOccupied:
    def test_free_tile_not_occupied(self):
        spawner = make_spawner(init_count=0)
        tile = {"x": 0, "y": 0, "is_boss": False}
        assert not spawner._tile_is_occupied(tile, [])

    def test_occupied_when_enemy_overlaps(self):
        spawner = make_spawner(init_count=0)
        from engine.encounter.enemy_sprite import COLLISION_OFFSET_X, COLLISION_OFFSET_Y, COLLISION_W, COLLISION_H
        tile = {"x": 0, "y": 0, "is_boss": False}
        # Enemy rect that overlaps the tile's collision area
        cx = COLLISION_OFFSET_X
        cy = COLLISION_OFFSET_Y
        occupied = [(cx, cy, COLLISION_W, COLLISION_H)]
        assert spawner._tile_is_occupied(tile, occupied)


# ── get_rects ─────────────────────────────────────────────────

class TestGetRects:
    def test_returns_all_active_rects(self):
        spawner = make_spawner(init_count=0)
        e1 = MagicMock(spec=EnemySprite)
        e1.collision_rect = (10, 20, 20, 18)
        e2 = MagicMock(spec=EnemySprite)
        e2.collision_rect = (100, 200, 20, 18)
        spawner._active = [e1, e2]
        rects = spawner.get_rects()
        assert (10, 20, 20, 18) in rects
        assert (100, 200, 20, 18) in rects
