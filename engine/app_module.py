# engine/app_module.py

from injector import Module, singleton, provider

from engine.settings import EngineSettings
from engine.ui.display import Display
from engine.util.frame_clock import FrameClock
from engine.scenes.scene_manager import SceneManager
from engine.scenes.scene_registry import SceneRegistry
from engine.game import Game
from engine.scenes.boot_scene import BootScene
from engine.scenes.item_scene import ItemScene
from engine.scenes.title_scene import TitleScene
from engine.scenes.name_entry_scene import NameEntryScene
from engine.scenes.world_map_scene import WorldMapScene
from engine.scenes.load_game_scene import LoadGameScene
from engine.scenes.status_scene import StatusScene
from engine.dto.game_state_holder import GameStateHolder
from engine.io.save_manager import GameStateManager
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.io.enemy_loader import EnemyLoader
from engine.encounter.encounter_resolver import EncounterResolver
from engine.encounter.encounter_manager import EncounterManager
from engine.io.item_catalog import ItemCatalog
from engine.item.item_effect_handler import ItemEffectHandler
from engine.item.item_logic import build_mc_catalog
from engine.world.world_map_logic import load_magic_cores
from engine.io.manifest_loader import ManifestLoader
from engine.world.tile_map_factory import TileMapFactory
from engine.io.npc_loader import NpcLoader
from engine.audio.bgm_manager import BgmManager


class AppModule(Module):
    def __init__(self, scenario_path: str) -> None:
        self._scenario_path = scenario_path

    @provider
    @singleton
    def provide_engine_settings(self) -> EngineSettings:
        return EngineSettings.load()

    @provider
    @singleton
    def provide_manifest_loader(self) -> ManifestLoader:
        return ManifestLoader(self._scenario_path)

    @provider
    @singleton
    def provide_display(self) -> Display:
        return Display()

    @provider
    @singleton
    def provide_frame_clock(self) -> FrameClock:
        return FrameClock()

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
        settings: EngineSettings,
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
    def provide_npc_loader(self, loader: ManifestLoader) -> NpcLoader:
        return NpcLoader(scenario_path=loader.scenario_path)

    @provider
    @singleton
    def provide_enemy_loader(self, loader: ManifestLoader) -> EnemyLoader:
        enemies_dir = loader.scenario_path / "data" / "enemies"
        classes_dir = loader.scenario_path / "data" / "classes"
        return EnemyLoader(enemies_dir=enemies_dir, classes_dir=classes_dir)

    @provider
    @singleton
    def provide_encounter_resolver(self, enemy_loader: EnemyLoader) -> EncounterResolver:
        return EncounterResolver(enemy_loader)

    @provider
    @singleton
    def provide_encounter_manager(
        self,
        resolver: EncounterResolver,
        loader: ManifestLoader,
    ) -> EncounterManager:
        encount_dir = loader.scenario_path / "data" / "encount"
        classes_dir = loader.scenario_path / "data" / "classes"
        return EncounterManager(resolver=resolver, encount_dir=encount_dir, classes_dir=classes_dir)

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
    def provide_bgm_manager(self) -> BgmManager:
        return BgmManager()

    @provider
    @singleton
    def provide_scene_registry(
        self,
        settings: EngineSettings,
        loader: ManifestLoader,
        scene_manager: SceneManager,
        holder: GameStateHolder,
        tile_map_factory: TileMapFactory,
        game_state_manager: GameStateManager,
        dialogue_engine: DialogueEngine,
        npc_loader: NpcLoader,
        encounter_manager: EncounterManager,
        item_catalog: ItemCatalog,
        effect_handler: ItemEffectHandler,
        bgm_manager: BgmManager,
    ) -> SceneRegistry:
        registry = SceneRegistry()
        mc_catalog = build_mc_catalog(load_magic_cores(loader.scenario_path))

        registry.register_singleton("boot", BootScene(scene_manager, loader, registry))

        registry.register_factory("title",
            lambda: TitleScene(loader, scene_manager, registry, game_state_manager))
        registry.register_factory("name_entry",
            lambda: NameEntryScene(loader, scene_manager, registry, holder,
                                   item_catalog=item_catalog,
                                   debug_party=settings.debug_party))
        registry.register_factory("load_game",
            lambda: LoadGameScene(game_state_manager, holder, scene_manager, registry))
        registry.register_factory("world_map",
            lambda: WorldMapScene(
                holder, loader, tile_map_factory,
                scene_manager, registry,
                game_state_manager, dialogue_engine, npc_loader,
                encounter_manager=encounter_manager,
                effect_handler=effect_handler,
                mc_catalog=mc_catalog,
                text_speed=settings.text_speed,
                smooth_collision=settings.smooth_collision,
                mc_exchange_confirm_large=settings.mc_exchange_confirm_large,
                bgm_manager=bgm_manager,
            ))
        registry.register_factory("status",
            lambda: StatusScene(
                holder=holder,
                scene_manager=scene_manager,
                registry=registry,
                scenario_path=str(loader.scenario_path),
                return_scene_name="world_map",
            ))
        registry.register_factory("items",
            lambda: ItemScene(
                holder=holder,
                scene_manager=scene_manager,
                registry=registry,
                effect_handler=effect_handler,
                mc_catalog=mc_catalog,
                use_aoe_confirm=settings.use_aoe_confirm,
            ))

        return registry

    @provider
    @singleton
    def provide_game(
        self,
        display: Display,
        clock: FrameClock,
        scene_manager: SceneManager,
        registry: SceneRegistry,
    ) -> Game:
        scene_manager.switch(registry.get("boot"))
        return Game(display, clock, scene_manager)
