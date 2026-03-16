# engine/core/scenes/boot_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.data.loader import ManifestLoader


class BootScene(Scene):
    def __init__(self, scene_manager: SceneManager, loader: ManifestLoader) -> None:
        self._scene_manager = scene_manager
        self._loader = loader
        self._done = False

    def update(self, delta: float) -> None:
        if self._done:
            return
        manifest = self._loader.load()
        # store manifest for later use — title scene will read it
        self._manifest = manifest
        self._done = True
        # transition to TitleScene (stub for now)
        from engine.core.scenes.title_scene import TitleScene
        self._scene_manager.switch(TitleScene(self._manifest))

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 0))