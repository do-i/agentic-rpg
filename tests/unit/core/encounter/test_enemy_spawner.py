# tests/unit/core/encounter/test_enemy_spawner.py

import pytest
from unittest.mock import MagicMock
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
from engine.util.pseudo_random import PseudoRandom

_rng = PseudoRandom(seed=0)


def make_zone(with_boss=False, spawn_frequency=None) -> EncounterZone:
    entries = EncounterSet([
        Formation(["goblin"], 60, chase_range=3),
        Formation(["bat"], 40, chase_range=2),
    ])
    boss = BossConfig("spider_boss", "Boss Spider", once=True,
                      flag_set="boss_defeated") if with_boss else None
    return EncounterZone(
        zone_id="zone_01", name="Forest", density=0.8,
        entries=entries, boss=boss,
        spawn_frequency=spawn_frequency,
    )


def make_spawn_tiles(count=3) -> list[dict]:
    return [{"x": i * 96, "y": i * 96} for i in range(count)]


def make_spawner(
    zone=None,
    spawn_tiles=None,
    map_interval=None,
    global_interval=30.0,
    boss_tile=None,
) -> EnemySpawner:
    if zone is None:
        zone = make_zone()
    if spawn_tiles is None:
        spawn_tiles = make_spawn_tiles(3)

    resolver = MagicMock()
    resolver.pick_formation.return_value = Formation(["goblin"], 100, chase_range=3)

    return EnemySpawner(
        zone=zone,
        spawn_tiles=spawn_tiles,
        map_interval=map_interval,
        global_interval=global_interval,
        resolver=resolver,
        scenario_path=Path("/fake"),
        tile_size=32,
        boss_tile=boss_tile,
        rng=_rng,
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
    def test_spawns_one_enemy_per_spawn_tile(self):
        spawner = make_spawner(spawn_tiles=make_spawn_tiles(4))
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        assert len(spawner._all_enemies) == 4

    def test_all_enemies_start_active(self):
        spawner = make_spawner(spawn_tiles=make_spawn_tiles(3))
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        assert all(e.active for e in spawner._all_enemies)

    def test_spawns_boss_when_not_defeated(self):
        zone = make_zone(with_boss=True)
        boss_tile = {"x": 500, "y": 500}
        spawner = make_spawner(zone=zone, spawn_tiles=make_spawn_tiles(2), boss_tile=boss_tile)
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        bosses = [e for e in spawner._all_enemies if e.is_boss]
        assert len(bosses) == 1

    def test_skips_boss_when_defeated(self):
        zone = make_zone(with_boss=True)
        boss_tile = {"x": 500, "y": 500}
        spawner = make_spawner(zone=zone, spawn_tiles=make_spawn_tiles(2), boss_tile=boss_tile)
        flags = MagicMock()
        flags.has_flag.return_value = True
        spawner.init_spawn(flags)
        bosses = [e for e in spawner._all_enemies if e.is_boss]
        assert len(bosses) == 0


# ── on_enemy_engaged ──────────────────────────────────────────

class TestOnEnemyEngaged:
    def test_deactivates_enemy(self):
        spawner = make_spawner()
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        enemy = spawner._all_enemies[0]
        spawner.on_enemy_engaged(enemy)
        assert not enemy.active

    def test_enemy_remains_in_pool(self):
        spawner = make_spawner()
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        before = len(spawner._all_enemies)
        spawner.on_enemy_engaged(spawner._all_enemies[0])
        assert len(spawner._all_enemies) == before

    def test_resets_spawn_timer(self):
        spawner = make_spawner(global_interval=30.0)
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        spawner._spawn_timer = 29.9
        spawner.on_enemy_engaged(spawner._all_enemies[0])
        assert spawner._spawn_timer == 0.0


# ── Respawn (reactivation) ────────────────────────────────────

class TestRespawn:
    def test_activates_inactive_enemy_after_interval(self):
        spawner = make_spawner(global_interval=1.0, spawn_tiles=make_spawn_tiles(1))
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)
        enemy = spawner._all_enemies[0]
        spawner.on_enemy_engaged(enemy)
        assert not enemy.active

        collision = MagicMock()
        collision.is_rect_blocked.return_value = False
        party = MagicMock()
        party.members = []

        # Advance past the interval
        spawner.update(1.1, 0.0, 0.0, collision, party)
        assert enemy.active

    def test_skips_when_all_active(self):
        spawner = make_spawner(global_interval=1.0, spawn_tiles=make_spawn_tiles(2))
        flags = MagicMock()
        flags.has_flag.return_value = False
        spawner.init_spawn(flags)

        collision = MagicMock()
        party = MagicMock()
        party.members = []

        # All active — timer fires but nothing should change
        spawner.update(1.1, 0.0, 0.0, collision, party)
        assert all(e.active for e in spawner._all_enemies)


# ── check_player_collision ────────────────────────────────────

class TestCheckPlayerCollision:
    def test_returns_none_when_no_enemies(self):
        spawner = make_spawner()
        result = spawner.check_player_collision((0, 0, 10, 10))
        assert result is None

    def test_returns_active_enemy_on_overlap(self):
        spawner = make_spawner()
        enemy = MagicMock(spec=EnemySprite)
        enemy.active = True
        enemy.collides_with.return_value = True
        spawner._all_enemies.append(enemy)
        assert spawner.check_player_collision((0, 0, 20, 18)) is enemy

    def test_ignores_inactive_enemy(self):
        spawner = make_spawner()
        enemy = MagicMock(spec=EnemySprite)
        enemy.active = False
        enemy.collides_with.return_value = True
        spawner._all_enemies.append(enemy)
        assert spawner.check_player_collision((0, 0, 20, 18)) is None

    def test_returns_none_when_no_overlap(self):
        spawner = make_spawner()
        enemy = MagicMock(spec=EnemySprite)
        enemy.active = True
        enemy.collides_with.return_value = False
        spawner._all_enemies.append(enemy)
        assert spawner.check_player_collision((9999, 9999, 20, 18)) is None


# ── get_rects ─────────────────────────────────────────────────

class TestGetRects:
    def test_returns_only_active_rects(self):
        spawner = make_spawner()
        e1 = MagicMock(spec=EnemySprite)
        e1.active = True
        e1.collision_rect = (10, 20, 20, 18)
        e2 = MagicMock(spec=EnemySprite)
        e2.active = False
        e2.collision_rect = (100, 200, 20, 18)
        spawner._all_enemies = [e1, e2]
        rects = spawner.get_rects()
        assert (10, 20, 20, 18) in rects
        assert (100, 200, 20, 18) not in rects


# ── active_enemies property ───────────────────────────────────

class TestActiveEnemies:
    def test_returns_only_active(self):
        spawner = make_spawner()
        e1 = MagicMock(spec=EnemySprite)
        e1.active = True
        e2 = MagicMock(spec=EnemySprite)
        e2.active = False
        spawner._all_enemies = [e1, e2]
        assert spawner.active_enemies == [e1]


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
