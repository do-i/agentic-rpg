# engine/core/app_module.py
# Changes from previous version:
#   - added EnemyLoader, EncounterResolver, EncounterManager providers
#   - world_map factory passes encounter_manager
#   - battle scene registered as factory

from injector import Module, singleton, provider

from engine.core.config.engine_settings import EngineSettings
from engine.core.display import Display
from engine.core.frame_clock import FrameClock
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.game import Game
from engine.core.scenes.boot_scene import BootScene
from engine.core.scenes.item_scene import ItemScene
from engine.core.scenes.title_scene import TitleScene
from engine.core.scenes.name_entry_scene import NameEntryScene
from engine.core.scenes.world_map_scene import WorldMapScene
from engine.core.scenes.load_game_scene import LoadGameScene
from engine.core.scenes.status_scene import StatusScene
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.game_state_manager import GameStateManager
from engine.core.dialogue.dialogue_engine import DialogueEngine
from engine.core.encounter.enemy_loader import EnemyLoader
from engine.core.encounter.encounter_resolver import EncounterResolver
from engine.core.encounter.encounter_manager import EncounterManager
from engine.data.loader import ManifestLoader
from engine.world.tile_map_factory import TileMapFactory
from engine.world.npc_loader import NpcLoader


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
    def provide_scene_manager(self) -> SceneManager:
        return SceneManager()

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
    def provide_game_state_manager(self, settings: EngineSettings) -> GameStateManager:
        return GameStateManager(saves_dir=settings.saves_dir)

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
        return EncounterManager(resolver=resolver, encount_dir=encount_dir)

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
    ) -> SceneRegistry:
        registry = SceneRegistry()

        registry.register_singleton("boot", BootScene(scene_manager, loader, registry))

        registry.register_factory("title",
            lambda: TitleScene(loader, scene_manager, registry, game_state_manager))
        registry.register_factory("name_entry",
            lambda: NameEntryScene(loader, scene_manager, registry, holder,
                                   debug_party=settings.debug_party))
        registry.register_factory("load_game",
            lambda: LoadGameScene(game_state_manager, holder, scene_manager, registry))
        registry.register_factory("world_map",
            lambda: WorldMapScene(
                holder, loader, tile_map_factory,
                scene_manager, registry,
                game_state_manager, dialogue_engine, npc_loader,
                encounter_manager=encounter_manager,
                text_speed=settings.text_speed,
                smooth_collision=settings.smooth_collision,
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
            lambda: ItemScene(holder, scene_manager, registry))

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
