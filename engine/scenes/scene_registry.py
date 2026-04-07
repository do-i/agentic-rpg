# engine/scenes/scene_registry.py

from typing import Callable
from engine.scenes.scene import Scene


class SceneRegistry:
    """
    Generic scene registry — no knowledge of specific scene types.
    AppModule owns all construction details.

    Singletons: pre-built, same instance returned every get().
    Factories:  callable, fresh instance returned every get().
    """

    def __init__(self) -> None:
        self._singletons: dict[str, Scene] = {}
        self._factories: dict[str, Callable[[], Scene]] = {}

    # ── Registration ──────────────────────────────────────────

    def register_singleton(self, name: str, scene: Scene) -> None:
        self._singletons[name] = scene

    def register_factory(self, name: str, factory: Callable[[], Scene]) -> None:
        self._factories[name] = factory

    # ── Retrieval ─────────────────────────────────────────────

    def get(self, name: str) -> Scene:
        """Singletons checked first, then factories."""
        if name in self._singletons:
            return self._singletons[name]
        if name in self._factories:
            return self._factories[name]()
        raise KeyError(f"Scene not registered: {name!r}")

    def __repr__(self) -> str:
        return (
            f"SceneRegistry("
            f"singletons={list(self._singletons.keys())}, "
            f"factories={list(self._factories.keys())})"
        )
