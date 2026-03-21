# engine/core/app_module.py

from injector import Module, singleton, provider

from engine.core.config.engine_settings import EngineSettings
from engine.core.display import Display
from engine.core.frame_clock import FrameClock
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.game import Game
from engine.core.scenes.boot_scene import BootScene
from engine.core.scenes.title_scene import TitleScene
from engine.core.scenes.name_entry_scene import NameEntryScene
from engine.core.scenes.world_map_scene import WorldMapScene
from engine.core.scenes.load_game_scene import LoadGameScene
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.game_state_manager import GameStateManager
from engine.core.dialogue.dialogue_engine import DialogueEngine
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
    def provide_npc_loader(self) -> NpcLoader:
        return NpcLoader()

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
    ) -> SceneRegistry:
        registry = SceneRegistry()

        registry.register_singleton("boot", BootScene(scene_manager, loader, registry))
        registry.register_factory("title",
            lambda: TitleScene(loader, scene_manager, registry, game_state_manager))
        registry.register_factory("name_entry",
            lambda: NameEntryScene(loader, scene_manager, registry, holder))
        registry.register_factory("load_game",
            lambda: LoadGameScene(game_state_manager, holder, scene_manager, registry))
        registry.register_factory("world_map",
            lambda: WorldMapScene(
                holder, loader, tile_map_factory,
                scene_manager, registry,
                game_state_manager, dialogue_engine, npc_loader,
                text_speed=settings.text_speed,
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
