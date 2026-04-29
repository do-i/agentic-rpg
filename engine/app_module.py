# engine/app_module.py

from injector import Module, singleton, provider

from engine.settings.engine_config_data import EngineConfigData
from engine.settings.balance_data import BalanceData
from engine.util.frame_clock import FrameClock
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.game import Game
from engine.common.game_state_holder import GameStateHolder
from engine.io.save_manager import GameStateManager
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.battle.enemy_loader import EnemyLoader
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.encounter_manager import EncounterManager
from engine.item.item_catalog import ItemCatalog
from engine.item.item_effect_handler import ItemEffectHandler
from engine.io.manifest_loader import ManifestLoader
from engine.scenes.scene_registrar import SceneDeps, register_scenes
from engine.world.tile_map_factory import TileMapFactory
from engine.world.npc_loader import NpcLoader
from engine.world.item_box_loader import ItemBoxLoader
from engine.world.sprite_sheet_cache import SpriteSheetCache
from engine.audio.bgm_manager import BgmManager
from engine.audio.sfx_manager import SfxManager
from engine.record.recorder import RecordPlaybackManager
from engine.util.pseudo_random import PseudoRandom
from engine.common.font_provider import FontProvider, init_fonts
import random as _random


class AppModule(Module):
    def __init__(self, scenario_path: str, mode: str = "normal", recording_file: str = "recording.pkl", playback_speed: float = 1.0, seed: int | None = None) -> None:
        self._scenario_path = scenario_path
        self._mode = mode
        self._recording_file = recording_file
        self._playback_speed = playback_speed
        self._seed = seed

    @provider
    @singleton
    def provide_engine_settings(self) -> EngineConfigData:
        return EngineConfigData.load()

    @provider
    @singleton
    def provide_font_provider(self, config: EngineConfigData, loader: ManifestLoader) -> FontProvider:
        manifest = loader.load()
        font_path = (manifest.get("font") or {}).get("path")
        resolved: str | None = None
        if isinstance(font_path, str):
            p = loader.scenario_path / font_path
            if p.exists():
                resolved = str(p)
        return init_fonts(resolved, config.font_sizes)

    @provider
    @singleton
    def provide_manifest_loader(self) -> ManifestLoader:
        return ManifestLoader(self._scenario_path)

    @provider
    @singleton
    def provide_balance_data(self, loader: ManifestLoader) -> BalanceData:
        return BalanceData.load(loader.scenario_path, loader.load())

    @provider
    @singleton
    def provide_frame_clock(self, config: EngineConfigData) -> FrameClock:
        return FrameClock(config.fps)

    @provider
    @singleton
    def provide_record_playback_manager(self) -> RecordPlaybackManager:
        return RecordPlaybackManager(self._mode, self._recording_file, self._playback_speed)

    @provider
    @singleton
    def provide_pseudo_random(self, recorder: RecordPlaybackManager) -> PseudoRandom:
        if self._mode == "playback":
            seed = recorder.session_seed
        else:
            seed = self._seed if self._seed is not None else _random.randrange(2 ** 32)
            recorder.set_seed(seed)
        return PseudoRandom(seed)

    @provider
    @singleton
    def provide_scene_manager(self, bgm_manager: BgmManager) -> SceneManager:
        return SceneManager(bgm_manager=bgm_manager)

    @provider
    @singleton
    def provide_game_state_holder(self) -> GameStateHolder:
        return GameStateHolder()

    @provider
    @singleton
    def provide_tile_map_factory(self) -> TileMapFactory:
        return TileMapFactory()

    @provider
    @singleton
    def provide_game_state_manager(
        self,
        settings: EngineConfigData,
        loader: ManifestLoader,
        item_catalog: ItemCatalog,
    ) -> GameStateManager:
        classes_dir = loader.scenario_path / "data" / "classes"
        return GameStateManager(
            saves_dir=settings.saves_dir,
            classes_dir=classes_dir,
            item_catalog=item_catalog,
        )

    @provider
    @singleton
    def provide_dialogue_engine(self, loader: ManifestLoader) -> DialogueEngine:
        return DialogueEngine(loader.scenario_path / "data" / "dialogue")

    @provider
    @singleton
    def provide_sprite_sheet_cache(self) -> SpriteSheetCache:
        return SpriteSheetCache()

    @provider
    @singleton
    def provide_npc_loader(
        self,
        loader: ManifestLoader,
        config: EngineConfigData,
        rng: PseudoRandom,
        sprite_cache: SpriteSheetCache,
    ) -> NpcLoader:
        return NpcLoader(
            scenario_path=loader.scenario_path,
            tile_size=config.tile_size,
            rng=rng,
            sprite_cache=sprite_cache,
        )

    @provider
    @singleton
    def provide_item_box_loader(self, loader: ManifestLoader, config: EngineConfigData) -> ItemBoxLoader:
        return ItemBoxLoader(manifest_loader=loader, tile_size=config.tile_size)

    @provider
    @singleton
    def provide_enemy_loader(self, loader: ManifestLoader) -> EnemyLoader:
        enemies_dir = loader.scenario_path / "data" / "enemies"
        classes_dir = loader.scenario_path / "data" / "classes"
        return EnemyLoader(enemies_dir=enemies_dir, classes_dir=classes_dir)

    @provider
    @singleton
    def provide_encounter_resolver(self, enemy_loader: EnemyLoader, rng: PseudoRandom) -> EncounterResolver:
        return EncounterResolver(enemy_loader, rng)

    @provider
    @singleton
    def provide_encounter_manager(
        self,
        loader: ManifestLoader,
        item_catalog: ItemCatalog,
    ) -> EncounterManager:
        encount_dir = loader.scenario_path / "data" / "encount"
        classes_dir = loader.scenario_path / "data" / "classes"
        return EncounterManager(
            encount_dir=encount_dir,
            classes_dir=classes_dir,
            item_catalog=item_catalog,
        )

    @provider
    @singleton
    def provide_item_catalog(self, loader: ManifestLoader) -> ItemCatalog:
        items_dir = loader.scenario_path / "data" / "items"
        return ItemCatalog(items_dir)

    @provider
    @singleton
    def provide_item_effect_handler(self, loader: ManifestLoader) -> ItemEffectHandler:
        field_use_path = loader.scenario_path / "data" / "items" / "field_use.yaml"
        return ItemEffectHandler(field_use_path)

    @provider
    @singleton
    def provide_bgm_manager(self, loader: ManifestLoader, config: EngineConfigData) -> BgmManager:
        return BgmManager(loader.scenario_path, enabled=config.bgm_enabled)

    @provider
    @singleton
    def provide_sfx_manager(self, loader: ManifestLoader, config: EngineConfigData) -> SfxManager:
        return SfxManager(loader.scenario_path, enabled=config.sfx_enabled)

    @provider
    @singleton
    def provide_scene_registry(
        self,
        settings: EngineConfigData,
        balance: BalanceData,
        loader: ManifestLoader,
        scene_manager: SceneManager,
        holder: GameStateHolder,
        tile_map_factory: TileMapFactory,
        game_state_manager: GameStateManager,
        dialogue_engine: DialogueEngine,
        npc_loader: NpcLoader,
        item_box_loader: ItemBoxLoader,
        encounter_manager: EncounterManager,
        encounter_resolver: EncounterResolver,
        item_catalog: ItemCatalog,
        effect_handler: ItemEffectHandler,
        bgm_manager: BgmManager,
        recorder: RecordPlaybackManager,
        sfx_manager: SfxManager,
        rng: PseudoRandom,
        sprite_cache: SpriteSheetCache,
    ) -> SceneRegistry:
        registry = SceneRegistry()
        register_scenes(registry, SceneDeps(
            settings=settings,
            balance=balance,
            loader=loader,
            scene_manager=scene_manager,
            holder=holder,
            tile_map_factory=tile_map_factory,
            game_state_manager=game_state_manager,
            dialogue_engine=dialogue_engine,
            npc_loader=npc_loader,
            item_box_loader=item_box_loader,
            encounter_manager=encounter_manager,
            encounter_resolver=encounter_resolver,
            item_catalog=item_catalog,
            effect_handler=effect_handler,
            bgm_manager=bgm_manager,
            recorder=recorder,
            sfx_manager=sfx_manager,
            rng=rng,
            sprite_cache=sprite_cache,
        ))
        return registry

    @provider
    @singleton
    def provide_game(
        self,
        config: EngineConfigData,
        clock: FrameClock,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        recorder: RecordPlaybackManager,
        font_provider: FontProvider,
        loader: ManifestLoader,
    ) -> Game:
        speed = self._playback_speed if self._mode == "playback" else 1.0
        scene_manager.switch(registry.get("boot"))
        window_title = loader.load().get("window_title", "")
        return Game(config, clock, scene_manager, recorder, window_title=window_title, playback_speed=speed)
