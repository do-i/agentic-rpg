# engine/scenes/scene_manager.py

from engine.scenes.scene import Scene


class SceneManager:
    def __init__(self) -> None:
        self._current: Scene | None = None

    def switch(self, scene: Scene) -> None:
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