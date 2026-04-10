# engine/scenes/scene_manager.py

from __future__ import annotations

from engine.scenes.scene import Scene


class SceneManager:
    def __init__(self, bgm_manager=None) -> None:
        self._current: Scene | None = None
        self._bgm_manager = bgm_manager

    def switch(self, scene: Scene) -> None:
        if self._bgm_manager:
            self._bgm_manager.stop()
        self._current = scene

    def handle_events(self, events: list) -> None:
        if self._current:
            self._current.handle_events(events)

    def update(self, delta: float) -> None:
        if self._current:
            self._current.update(delta)

    def render(self, screen) -> None:
        if self._current:
            self._current.render(screen)