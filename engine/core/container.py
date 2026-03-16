# engine/core/container.py

from dependency_injector import containers, providers
from engine.core.display import Display
from engine.core.frame_clock import FrameClock
from engine.core.scene_manager import SceneManager
from engine.core.game import Game
from engine.data.loader import ManifestLoader
from engine.core.scenes.boot_scene import BootScene


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    display = providers.Singleton(Display)
    clock = providers.Singleton(FrameClock)
    scene_manager = providers.Singleton(SceneManager)
    manifest_loader = providers.Singleton(
        ManifestLoader,
        scenario_path=config.scenario_path,
    )
    boot_scene = providers.Singleton(
        BootScene,
        scene_manager=scene_manager,
        loader=manifest_loader,
    )
    game = providers.Singleton(
        Game,
        display=display,
        clock=clock,
        scene_manager=scene_manager,
    )