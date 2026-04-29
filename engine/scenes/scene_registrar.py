# engine/scenes/scene_registrar.py
#
# Pure scene-registration body extracted from AppModule.provide_scene_registry
# so the DI module is wiring-only. Takes a SceneRegistry and the bag of
# dependencies the scenes need; mutates the registry in place. No DI
# annotations here — this file knows nothing about injector.

from __future__ import annotations

from dataclasses import dataclass

from engine.audio.bgm_manager import BgmManager
from engine.audio.sfx_manager import SfxManager
from engine.common.game_state_holder import GameStateHolder
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.encounter.encounter_manager import EncounterManager
from engine.encounter.encounter_resolver import EncounterResolver
from engine.equipment.equip_scene import EquipScene
from engine.field_menu.field_menu_scene import FieldMenuScene
from engine.io.manifest_loader import ManifestLoader
from engine.io.save_manager import GameStateManager
from engine.item.item_catalog import ItemCatalog
from engine.item.item_effect_handler import ItemEffectHandler
from engine.item.item_scene import ItemScene
from engine.item.magic_core_catalog_state import build_mc_catalog
from engine.record.recorder import RecordPlaybackManager
from engine.settings.balance_data import BalanceData
from engine.settings.engine_config_data import EngineConfigData
from engine.spell.spell_scene import SpellScene
from engine.status.status_scene import StatusScene
from engine.title.boot_scene import BootScene
from engine.title.load_game_scene import LoadGameScene
from engine.title.name_entry_scene import NameEntryScene
from engine.title.title_scene import TitleScene
from engine.util.pseudo_random import PseudoRandom
from engine.world.item_box_loader import ItemBoxLoader
from engine.world.npc_loader import NpcLoader
from engine.world.sprite_sheet_cache import SpriteSheetCache
from engine.world.tile_map_factory import TileMapFactory
from engine.world.world_map_logic import load_magic_cores
from engine.world.world_map_scene import WorldMapScene


@dataclass(frozen=True)
class SceneDeps:
    """Bag of dependencies for register_scenes. Frozen so callers can't
    mutate it after construction; kw-only at the construction site keeps
    the registration body readable."""
    settings: EngineConfigData
    balance: BalanceData
    loader: ManifestLoader
    scene_manager: SceneManager
    holder: GameStateHolder
    tile_map_factory: TileMapFactory
    game_state_manager: GameStateManager
    dialogue_engine: DialogueEngine
    npc_loader: NpcLoader
    item_box_loader: ItemBoxLoader
    encounter_manager: EncounterManager
    encounter_resolver: EncounterResolver
    item_catalog: ItemCatalog
    effect_handler: ItemEffectHandler
    bgm_manager: BgmManager
    recorder: RecordPlaybackManager
    sfx_manager: SfxManager
    rng: PseudoRandom
    sprite_cache: SpriteSheetCache


def register_scenes(registry: SceneRegistry, deps: SceneDeps) -> None:
    """Register every scene in `registry`. Called from AppModule's
    SceneRegistry provider; tests can call it directly with stubs."""

    settings = deps.settings
    balance = deps.balance
    loader = deps.loader
    scene_manager = deps.scene_manager
    holder = deps.holder
    game_state_manager = deps.game_state_manager
    item_catalog = deps.item_catalog
    effect_handler = deps.effect_handler
    bgm_manager = deps.bgm_manager
    sfx_manager = deps.sfx_manager

    mc_catalog = build_mc_catalog(load_magic_cores(loader.scenario_path))

    registry.register_singleton("boot", BootScene(scene_manager, loader, registry))

    registry.register_factory("title",
        lambda: TitleScene(loader, scene_manager, registry, game_state_manager,
                           sfx_manager=sfx_manager,
                           bgm_manager=bgm_manager))
    registry.register_factory("name_entry",
        lambda: NameEntryScene(loader, scene_manager, registry, holder,
                               item_catalog=item_catalog,
                               debug_party=settings.debug_party,
                               sfx_manager=sfx_manager))
    registry.register_factory("load_game",
        lambda: LoadGameScene(game_state_manager, holder, scene_manager, registry,
                              sfx_manager=sfx_manager))
    registry.register_singleton("world_map", WorldMapScene(
            holder, loader, deps.tile_map_factory,
            scene_manager, registry,
            game_state_manager, deps.dialogue_engine, deps.npc_loader,
            item_box_loader=deps.item_box_loader,
            item_catalog=item_catalog,
            encounter_manager=deps.encounter_manager,
            encounter_resolver=deps.encounter_resolver,
            enemy_spawn_global_interval=settings.enemy_spawn_global_interval,
            effect_handler=effect_handler,
            mc_catalog=mc_catalog,
            text_speed=settings.text_speed,
            smooth_collision=settings.smooth_collision,
            mc_exchange_confirm_large=settings.mc_exchange_confirm_large,
            bgm_manager=bgm_manager,
            sfx_manager=sfx_manager,
            screen_width=settings.screen_width,
            screen_height=settings.screen_height,
            tile_size=settings.tile_size,
            fps=settings.fps,
            player_speed=balance.player_speed,
            debug_collision=settings.debug_collision,
            balance=balance,
            recorder=deps.recorder,
            rng=deps.rng,
            sprite_cache=deps.sprite_cache,
        ))
    registry.register_factory("status",
        lambda: StatusScene(
            holder=holder,
            scene_manager=scene_manager,
            registry=registry,
            scenario_path=str(loader.scenario_path),
            return_scene_name="world_map",
            sfx_manager=sfx_manager,
        ))
    registry.register_factory("items",
        lambda: ItemScene(
            holder=holder,
            scene_manager=scene_manager,
            registry=registry,
            effect_handler=effect_handler,
            mc_catalog=mc_catalog,
            use_aoe_confirm=settings.use_aoe_confirm,
            sfx_manager=sfx_manager,
        ))
    registry.register_factory("field_menu",
        lambda: FieldMenuScene(
            holder=holder,
            scene_manager=scene_manager,
            registry=registry,
            game_state_manager=game_state_manager,
            return_scene_name="world_map",
            sfx_manager=sfx_manager,
        ))
    registry.register_factory("equip",
        lambda: EquipScene(
            holder=holder,
            scene_manager=scene_manager,
            registry=registry,
            catalog=item_catalog,
            return_scene_name="world_map",
            sfx_manager=sfx_manager,
        ))
    registry.register_factory("spells",
        lambda: SpellScene(
            holder=holder,
            scene_manager=scene_manager,
            registry=registry,
            scenario_path=str(loader.scenario_path),
            return_scene_name="world_map",
            sfx_manager=sfx_manager,
        ))
