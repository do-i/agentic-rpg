# engine/encounter/enemy_spawner.py
#
# Manages visible enemy sprites on the world map:
#   - Initial spawning at map load
#   - Timer-based respawning (up to max cap)
#   - Modifiers from party composition (Rogue/accessories)
#   - Spawn tile selection (dedicated TMX points)

from __future__ import annotations

import random
import time
from pathlib import Path

from engine.encounter.encounter_zone_data import EncounterZone, Formation
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.enemy_sprite import EnemySprite
from engine.battle.enemy_loader import EnemyLoader
from engine.world.sprite_sheet import SpriteSheet

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.common.flag_state import FlagState
    from engine.party.party_state import PartyState
    from engine.world.collision import CollisionMap

# Modifier constants
ROGUE_CHASE_REDUCTION      = 2   # tiles
STEALTH_CLOAK_REDUCTION    = 3   # tiles
LURE_CHARM_INTERVAL_MULT   = 0.5 # halves the spawn interval


class EnemySpawner:
    """
    Owns all active EnemySprite instances for the current map.

    Interval resolution priority:
        map YAML interval  >  zone.spawn_frequency  >  global_interval
    """

    def __init__(
        self,
        zone: EncounterZone,
        spawn_tiles: list[dict],          # [{x, y, is_boss}] from TMX enemy_spawns layer
        init_count: int,
        max_count: int,
        map_interval: float | None,       # from map YAML enemy_spawn.interval (may be None)
        global_interval: float,           # from settings.yaml
        resolver: EncounterResolver,
        enemy_loader: EnemyLoader,
        scenario_path: Path,
        tile_size: int = 32,
    ) -> None:
        self._zone          = zone
        self._spawn_tiles   = spawn_tiles
        self._init_count    = init_count
        self._max_count     = max_count
        self._resolver      = resolver
        self._enemy_loader  = enemy_loader
        self._scenario_path = scenario_path
        self._tile_size     = tile_size

        # Resolve base interval (map > zone > global)
        if map_interval is not None:
            self._base_interval = map_interval
        elif zone.spawn_frequency is not None:
            self._base_interval = zone.spawn_frequency
        else:
            self._base_interval = global_interval

        self._active: list[EnemySprite] = []
        self._respawn_queue: list[tuple[Formation, bool, float]] = []
        # ^ (formation, is_boss, defeat_time)

        self._spawn_timer   = 0.0
        self._sprite_cache: dict[str, SpriteSheet | None] = {}

    # ── Public API ────────────────────────────────────────────────

    def init_spawn(self, flags: FlagState) -> None:
        """Spawn initial enemies at map load. Called once from WorldMapScene._init()."""
        # Spawn boss if present and not defeated
        boss = self._zone.boss
        if boss and not (boss.once and boss.flag_set and flags.has_flag(boss.flag_set)):
            boss_tile = self._find_boss_tile() or self._find_free_tile()
            if boss_tile:
                self._spawn_boss(boss_tile)

        # Spawn regular enemies up to init_count
        spawned = 0
        for _ in range(self._init_count * 3):   # retry budget
            if spawned >= self._init_count:
                break
            if len(self._active) >= self._max_count:
                break
            tile = self._find_free_tile()
            if tile is None:
                break
            formation = self._resolver.pick_formation(self._zone)
            if formation:
                self._create_enemy(formation, tile, is_boss=False)
                spawned += 1

    def update(
        self,
        delta: float,
        player_px: float,
        player_py: float,
        collision_map: CollisionMap | None,
        party: PartyState | None,
    ) -> None:
        """Per-frame update. Call from WorldMapScene.update()."""
        interval_mult, chase_reduction = self._compute_modifiers(party)
        effective_interval = self._base_interval * interval_mult

        # Process respawn queue
        now = time.monotonic()
        still_waiting: list[tuple[Formation, bool, float]] = []
        for formation, is_boss, defeat_time in self._respawn_queue:
            if now - defeat_time >= effective_interval:
                if len(self._active) < self._max_count:
                    tile = self._find_boss_tile() if is_boss else self._find_free_tile()
                    if tile:
                        self._create_enemy(formation, tile, is_boss=is_boss)
                    else:
                        still_waiting.append((formation, is_boss, defeat_time))
                else:
                    still_waiting.append((formation, is_boss, defeat_time))
            else:
                still_waiting.append((formation, is_boss, defeat_time))
        self._respawn_queue = still_waiting

        # Update active enemy sprites
        all_rects = [e.collision_rect for e in self._active]
        for enemy in self._active:
            other_rects = [r for e, r in zip(self._active, all_rects) if e is not enemy]
            eff_chase = max(0, enemy.chase_range - chase_reduction)
            enemy.update(delta, player_px, player_py, collision_map, other_rects, eff_chase)

        # Tick spawn timer
        self._spawn_timer += delta
        if self._spawn_timer >= effective_interval:
            self._spawn_timer = 0.0
            self._try_spawn_one()

    def check_player_collision(
        self, player_rect: tuple[int, int, int, int]
    ) -> EnemySprite | None:
        """Return the first active enemy that overlaps the player's collision rect."""
        for enemy in self._active:
            if enemy.collides_with(player_rect):
                return enemy
        return None

    def on_enemy_defeated(self, enemy: EnemySprite) -> None:
        """Remove enemy from active list and queue it for respawn."""
        if enemy in self._active:
            self._active.remove(enemy)
        formation_obj = Formation(
            enemy_ids=enemy.formation,
            weight=1,
            chase_range=enemy.chase_range,
        )
        self._respawn_queue.append((formation_obj, enemy.is_boss, time.monotonic()))

    def get_rects(self) -> list[tuple[int, int, int, int]]:
        """Return all active enemy collision rects (for player/NPC collision)."""
        return [e.collision_rect for e in self._active]

    @property
    def active_enemies(self) -> list[EnemySprite]:
        return list(self._active)

    # ── Modifier computation ──────────────────────────────────────

    def _compute_modifiers(
        self, party: PartyState | None
    ) -> tuple[float, int]:
        """
        Returns (interval_multiplier, chase_range_reduction).
        interval_multiplier < 1 means faster spawns.
        """
        if party is None:
            return 1.0, 0

        interval_mult    = 1.0
        chase_reduction  = 0

        for member in party.members:
            if member.class_name.lower() == "rogue":
                chase_reduction += ROGUE_CHASE_REDUCTION
                acc = member.equipped.get("accessory", "")
                if acc == "stealth_cloak":
                    chase_reduction += STEALTH_CLOAK_REDUCTION
                elif acc == "lure_charm":
                    interval_mult = min(interval_mult, LURE_CHARM_INTERVAL_MULT)

        return interval_mult, chase_reduction

    # ── Spawning helpers ──────────────────────────────────────────

    def _try_spawn_one(self) -> None:
        """Attempt a single spawn tick: density check → free tile → create enemy."""
        if len(self._active) >= self._max_count:
            return
        if not self._spawn_tiles:
            return
        if random.random() > self._zone.density:
            return
        tile = self._find_free_tile()
        if tile is None:
            return
        formation = self._resolver.pick_formation(self._zone)
        if formation:
            self._create_enemy(formation, tile, is_boss=False)

    def _create_enemy(
        self,
        formation: Formation,
        tile: dict,
        is_boss: bool,
    ) -> EnemySprite:
        tx = tile["x"] // self._tile_size
        ty = tile["y"] // self._tile_size
        first_id = formation.enemy_ids[0] if formation.enemy_ids else ""
        sprite_sheet = self._load_sprite(first_id)
        enemy = EnemySprite(
            formation=list(formation.enemy_ids),
            tile_x=tx,
            tile_y=ty,
            is_boss=is_boss,
            chase_range=formation.chase_range,
            sprite_sheet=sprite_sheet,
            tile_size=self._tile_size,
        )
        self._active.append(enemy)
        return enemy

    def _spawn_boss(self, tile: dict) -> None:
        boss = self._zone.boss
        if not boss:
            return
        formation = Formation(
            enemy_ids=[boss.enemy_id],
            weight=1,
            chase_range=0,
        )
        self._create_enemy(formation, tile, is_boss=True)

    def _find_free_tile(self) -> dict | None:
        """Find a spawn tile not currently occupied by any active enemy."""
        regular_tiles = [t for t in self._spawn_tiles if not t.get("is_boss")]
        random.shuffle(regular_tiles)
        occupied_rects = [e.collision_rect for e in self._active]
        for tile in regular_tiles:
            if not self._tile_is_occupied(tile, occupied_rects):
                return tile
        return None

    def _find_boss_tile(self) -> dict | None:
        """Find the dedicated boss spawn tile if one exists."""
        boss_tiles = [t for t in self._spawn_tiles if t.get("is_boss")]
        if not boss_tiles:
            return None
        occupied_rects = [e.collision_rect for e in self._active]
        for tile in boss_tiles:
            if not self._tile_is_occupied(tile, occupied_rects):
                return tile
        return None

    def _tile_is_occupied(
        self,
        tile: dict,
        occupied_rects: list[tuple[int, int, int, int]],
    ) -> bool:
        """True if any active enemy's collision rect overlaps the spawn tile area."""
        from engine.encounter.enemy_sprite import COLLISION_OFFSET_X, COLLISION_OFFSET_Y, COLLISION_W, COLLISION_H
        tile_px = tile["x"]
        tile_py = tile["y"]
        cx = tile_px + COLLISION_OFFSET_X
        cy = tile_py + COLLISION_OFFSET_Y
        for ox, oy, ow, oh in occupied_rects:
            if cx < ox + ow and cx + COLLISION_W > ox and cy < oy + oh and cy + COLLISION_H > oy:
                return True
        return False

    # ── Sprite loading ────────────────────────────────────────────

    def _load_sprite(self, enemy_id: str) -> SpriteSheet | None:
        if enemy_id in self._sprite_cache:
            return self._sprite_cache[enemy_id]
        sprite_sheet = None
        sprite_path_str = self._enemy_loader.load_world_sprite_path(enemy_id)
        if sprite_path_str:
            full_path = self._scenario_path / sprite_path_str
            if full_path.exists():
                try:
                    sprite_sheet = SpriteSheet(full_path)
                except Exception as e:
                    print(f"[WARN] failed to load enemy world sprite {full_path}: {e}")
        self._sprite_cache[enemy_id] = sprite_sheet
        return sprite_sheet
