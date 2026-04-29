# engine/encounter/enemy_spawner.py
#
# Manages visible enemy sprites on the world map:
#   - Initial spawning at map load (one per spawn tile, all active)
#   - On battle: enemy deactivates (invisible/inactive)
#   - Timer-based reactivation: every interval, one random inactive enemy becomes active
#   - Modifiers from party composition (Rogue/accessories)
#   - Spawn tile positions come from the 'spawn_tile' TMX tile layer

from __future__ import annotations

from pathlib import Path

from engine.encounter.encounter_zone_data import EncounterZone, Formation
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.enemy_sprite import EnemySprite
from engine.world.sprite_sheet import SpriteSheet
from engine.world.sprite_sheet_cache import SpriteSheetCache
from engine.util.pseudo_random import PseudoRandom

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.common.flag_state import FlagState
    from engine.party.party_state import PartyState
    from engine.world.collision import CollisionMap

# Fallback modifier values — authoritative values live in the scenario
# balance YAML and flow in through the `balance` parameter.
ROGUE_CHASE_REDUCTION      = 2   # tiles
STEALTH_CLOAK_REDUCTION    = 3   # tiles
LURE_CHARM_INTERVAL_MULT   = 0.5 # halves the spawn interval


class EnemySpawner:
    """
    Owns all EnemySprite instances for the current map as a fixed pool.

    At init, one enemy is created per spawn tile — all active.
    When the player engages an enemy (battle starts), that enemy deactivates.
    Every interval, one random inactive enemy is reactivated.

    Interval resolution priority:
        map YAML interval  >  zone.spawn_frequency  >  global_interval
    """

    def __init__(
        self,
        zone: EncounterZone,
        spawn_tiles: list[dict],          # [{x, y}] spawn points from TMX spawn_tile layer
        map_interval: float | None,       # from map YAML enemy_spawn.interval (may be None)
        global_interval: float,           # from settings.yaml
        resolver: EncounterResolver,
        scenario_path: Path,
        rng: PseudoRandom,
        sprite_cache: SpriteSheetCache | None = None,
        tile_size: int = 32,
        boss_tile: dict | None = None,    # {x, y} boss spawn position from TMX boss_enemy layer
        balance=None,                     # BalanceData — spawner modifier values
    ) -> None:
        self._zone          = zone
        self._spawn_tiles   = spawn_tiles
        self._boss_tile     = boss_tile
        self._resolver      = resolver
        self._scenario_path = scenario_path
        self._rng           = rng
        self._sprite_cache  = sprite_cache or SpriteSheetCache()
        self._tile_size     = tile_size
        self._rogue_chase_reduction    = balance.rogue_chase_reduction    if balance else ROGUE_CHASE_REDUCTION
        self._stealth_cloak_reduction  = balance.stealth_cloak_reduction  if balance else STEALTH_CLOAK_REDUCTION
        self._lure_charm_interval_mult = balance.lure_charm_interval_mult if balance else LURE_CHARM_INTERVAL_MULT

        # Resolve base interval (map > zone > global)
        if map_interval is not None:
            self._base_interval = map_interval
        elif zone.spawn_frequency is not None:
            self._base_interval = zone.spawn_frequency
        else:
            self._base_interval = global_interval

        self._all_enemies: list[EnemySprite] = []
        self._elapsed     = 0.0
        self._spawn_timer = 0.0

    # ── Public API ────────────────────────────────────────────────

    def init_spawn(self, flags: FlagState) -> None:
        """Create one enemy per spawn tile (all active). Called once from WorldMapScene._init()."""
        # Spawn boss if present and not defeated
        boss = self._zone.boss
        if boss and not (boss.once and boss.flag_set and flags.has_flag(boss.flag_set)):
            if self._boss_tile:
                self._create_enemy(
                    Formation(enemy_ids=[boss.enemy_id], weight=1, chase_range=0),
                    self._boss_tile,
                    is_boss=True,
                )

        # One enemy per spawn tile
        for tile in self._spawn_tiles:
            formation = self._resolver.pick_formation(self._zone)
            if formation:
                self._create_enemy(formation, tile, is_boss=False)

    def update(
        self,
        delta: float,
        player_px: float,
        player_py: float,
        collision_map: CollisionMap | None,
        party: PartyState | None,
    ) -> None:
        """Per-frame update. Call from WorldMapScene.update()."""
        self._elapsed += delta
        interval_mult, chase_reduction = self._compute_modifiers(party)
        effective_interval = self._base_interval * interval_mult

        # Tick spawn timer — reactivate one inactive enemy when ready
        self._spawn_timer += delta
        if self._spawn_timer >= effective_interval:
            self._spawn_timer = 0.0
            self._try_activate_one()

        # Update active enemies. Build the rect list once and slice around
        # each enemy's index so we avoid the O(N^2) zip-and-filter pattern.
        active = [e for e in self._all_enemies if e.active]
        all_rects = [e.collision_rect for e in active]
        for i, enemy in enumerate(active):
            other_rects = all_rects[:i] + all_rects[i + 1:]
            eff_chase = max(0, enemy.chase_range - chase_reduction)
            enemy.update(delta, player_px, player_py, collision_map, other_rects, eff_chase)

    def check_player_collision(
        self, player_rect: tuple[int, int, int, int]
    ) -> EnemySprite | None:
        """Return the first active enemy that overlaps the player's collision rect."""
        for enemy in self._all_enemies:
            if enemy.active and enemy.collides_with(player_rect):
                return enemy
        return None

    def on_enemy_engaged(self, enemy: EnemySprite) -> None:
        """Deactivate enemy when player starts a battle with it. Resets the spawn timer
        so the player always waits the full interval before a new enemy appears.
        """
        enemy.deactivate()
        self._spawn_timer = 0.0

    def get_rects(self) -> list[tuple[int, int, int, int]]:
        """Return collision rects for all active enemies."""
        return [e.collision_rect for e in self._all_enemies if e.active]

    @property
    def active_enemies(self) -> list[EnemySprite]:
        return [e for e in self._all_enemies if e.active]

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
                chase_reduction += self._rogue_chase_reduction
                acc = member.equipped.get("accessory", "")
                if acc == "stealth_cloak":
                    chase_reduction += self._stealth_cloak_reduction
                elif acc == "lure_charm":
                    interval_mult = min(interval_mult, self._lure_charm_interval_mult)

        return interval_mult, chase_reduction

    # ── Spawning helpers ──────────────────────────────────────────

    def _try_activate_one(self) -> None:
        """Pick a random inactive enemy and activate it. No-op if all are active."""
        inactive = [e for e in self._all_enemies if not e.active]
        if inactive:
            self._rng.choice(inactive).activate()

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
            rng=self._rng,
            tile_size=self._tile_size,
        )
        self._all_enemies.append(enemy)
        return enemy

    # ── Sprite loading ────────────────────────────────────────────

    def _load_sprite(self, enemy_id: str) -> SpriteSheet | None:
        tsx_path = self._scenario_path / "assets" / "sprites" / "enemies" / f"{enemy_id}.tsx"
        return self._sprite_cache.get(tsx_path)
