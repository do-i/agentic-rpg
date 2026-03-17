# engine/core/app_module.py

from injector import Module, singleton, provider
from engine.core.display import Display
from engine.core.frame_clock import FrameClock
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.game import Game
from engine.core.scenes.boot_scene import BootScene
from engine.core.scenes.title_scene import TitleScene
from engine.core.scenes.name_entry_scene import NameEntryScene
from engine.data.loader import ManifestLoader


class AppModule(Module):
    def __init__(self, scenario_path: str) -> None:
        self._scenario_path = scenario_path

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
    def provide_scene_registry(
        self,
        loader: ManifestLoader,
        scene_manager: SceneManager,
    ) -> SceneRegistry:
        registry = SceneRegistry()

        # build boot scene first — singleton, no registry needed at construction
        boot = BootScene(scene_manager, loader, registry)
        registry.register_singleton("boot", boot)

        # factories — fresh instance each switch, registry passed in
        registry.register_factory("title",
            lambda: TitleScene(loader, scene_manager, registry))
        registry.register_factory("name_entry",
            lambda: NameEntryScene(loader, scene_manager, registry))
        # world_map — Phase 1
        # registry.register_factory("world_map",
        #     lambda: WorldMapScene(loader, scene_manager, registry))

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
