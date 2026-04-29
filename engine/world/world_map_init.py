# engine/world/world_map_init.py
#
# Map-load assembly: builds the tile map, camera, player, NPC/box lists, and
# enemy spawner from the current scenario manifest + map YAML. Extracted from
# WorldMapScene so the scene class can stay focused on per-frame orchestration.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.audio.bgm_manager import BgmManager
from engine.common.game_state_holder import GameStateHolder
from engine.encounter.encounter_manager import EncounterManager
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.enemy_spawner import EnemySpawner
from engine.io.manifest_loader import ManifestLoader
from engine.io.yaml_loader import load_yaml_optional
from engine.world.camera import Camera
from engine.world.item_box import ItemBox
from engine.world.item_box_loader import ItemBoxLoader
from engine.world.npc import Npc
from engine.world.npc_loader import NpcLoader
from engine.world.player import Player
from engine.world.sprite_sheet import SpriteSheet
from engine.world.sprite_sheet_cache import SpriteSheetCache
from engine.world.tile_map import TileMap
from engine.world.tile_map_factory import TileMapFactory


@dataclass
class WorldMapInitResult:
    tile_map: TileMap
    camera: Camera
    player: Player
    npcs: list[Npc]
    item_boxes: list[ItemBox]
    enemy_spawner: EnemySpawner | None


def init_world_map(
    *,
    holder: GameStateHolder,
    loader: ManifestLoader,
    tile_map_factory: TileMapFactory,
    npc_loader: NpcLoader,
    item_box_loader: ItemBoxLoader,
    encounter_manager: EncounterManager,
    encounter_resolver: EncounterResolver | None,
    bgm_manager: BgmManager | None,
    sprite_cache: SpriteSheetCache | None,
    balance,
    rng,
    screen_width: int,
    screen_height: int,
    tile_size: int,
    fps: int,
    smooth_collision: bool,
    player_speed: int,
    debug_collision: bool,
    enemy_spawn_global_interval: float,
) -> WorldMapInitResult:
    scenario_path = loader.scenario_path
    manifest = loader.load()
    state = holder.get()
    map_id = state.map.current
    if sprite_cache is None:
        sprite_cache = SpriteSheetCache()

    tmx_path = scenario_path / "assets" / "maps" / f"{map_id}.tmx"
    tile_map = tile_map_factory.create(str(tmx_path))
    camera = Camera(
        tile_map.width_px, tile_map.height_px,
        screen_width, screen_height,
    )

    sprite_sheet = _load_protagonist_sprite(manifest, scenario_path, sprite_cache)
    player = Player(
        start=state.map.position,
        map_width_px=tile_map.width_px,
        map_height_px=tile_map.height_px,
        sprite_sheet=sprite_sheet,
        smooth_collision=smooth_collision,
        tile_size=tile_size,
        fps=fps,
        player_speed=player_speed,
        debug_collision=debug_collision,
    )

    if balance is not None:
        state.repository.configure_caps(balance)

    map_yaml_path = scenario_path / "data" / "maps" / f"{map_id}.yaml"
    map_data = load_yaml_optional(map_yaml_path) or {}

    npcs = npc_loader.parse_from_map_data(map_data)
    item_boxes = item_box_loader.parse_from_map_data(map_data)

    if map_data:
        state.map.display_name = map_data.get("name", map_id)
        if bgm_manager:
            bgm_key = map_data.get("bgm")
            if bgm_key:
                bgm_manager.play_key(bgm_key)

    encounter_manager.set_zone(map_id)
    enemy_spawner = _build_spawner(
        tile_map=tile_map,
        map_data=map_data,
        encounter_manager=encounter_manager,
        encounter_resolver=encounter_resolver,
        scenario_path=scenario_path,
        rng=rng,
        sprite_cache=sprite_cache,
        tile_size=tile_size,
        balance=balance,
        global_interval=enemy_spawn_global_interval,
    )
    if enemy_spawner is not None:
        enemy_spawner.init_spawn(state.flags)

    return WorldMapInitResult(
        tile_map=tile_map,
        camera=camera,
        player=player,
        npcs=npcs,
        item_boxes=item_boxes,
        enemy_spawner=enemy_spawner,
    )


def _build_spawner(
    *,
    tile_map: TileMap,
    map_data: dict,
    encounter_manager: EncounterManager,
    encounter_resolver: EncounterResolver | None,
    scenario_path: Path,
    rng,
    sprite_cache: SpriteSheetCache,
    tile_size: int,
    balance,
    global_interval: float,
) -> EnemySpawner | None:
    """Create an EnemySpawner if this map has an encounter zone and spawn tiles."""
    zone = encounter_manager.get_zone()
    if zone is None:
        return None
    if encounter_resolver is None:
        return None
    if not tile_map.enemy_spawn_tiles:
        return None

    map_interval: float | None = None
    spawn_cfg = map_data.get("enemy_spawn") or {}
    raw_interval = spawn_cfg.get("interval")
    if raw_interval is not None:
        map_interval = float(raw_interval)

    return EnemySpawner(
        zone=zone,
        spawn_tiles=tile_map.enemy_spawn_tiles,
        map_interval=map_interval,
        global_interval=global_interval,
        resolver=encounter_resolver,
        scenario_path=scenario_path,
        rng=rng,
        sprite_cache=sprite_cache,
        tile_size=tile_size,
        boss_tile=tile_map.boss_spawn_tile,
        balance=balance,
    )


def _load_protagonist_sprite(
    manifest: dict, scenario_path: Path, sprite_cache: SpriteSheetCache,
) -> SpriteSheet | None:
    sprite_path = manifest.get("protagonist", {}).get("sprite")
    if not sprite_path:
        return None
    return sprite_cache.get(scenario_path / sprite_path)
