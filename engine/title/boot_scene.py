# engine/scenes/boot_scene.py

from __future__ import annotations

import pygame
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.io.manifest_loader import ManifestLoader


class BootScene(Scene):
    def __init__(
        self,
        scene_manager: SceneManager,
        loader: ManifestLoader,
        registry: SceneRegistry,
    ) -> None:
        self._scene_manager = scene_manager
        self._loader = loader
        self._registry = registry
        self._done = False

    def update(self, delta: float) -> None:
        if self._done:
            return
        self._loader.load()  # warm up — validates manifest exists
        self._done = True
        self._scene_manager.switch(self._registry.get("title"))

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 0))
