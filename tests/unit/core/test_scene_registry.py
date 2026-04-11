# tests/unit/core/test_scene_registry.py

import pytest
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.scene.scene import Scene


# ── Minimal stub scene for testing ───────────────────────────

class StubScene(Scene):
    """Minimal Scene subclass — no pygame, no logic."""
    def __init__(self, name: str = "stub") -> None:
        self.name = name


# ── register_singleton ────────────────────────────────────────

class TestRegisterSingleton:
    def test_get_returns_registered_instance(self):
        r = SceneRegistry()
        scene = StubScene("boot")
        r.register_singleton("boot", scene)
        assert r.get("boot") is scene

    def test_get_returns_same_instance_every_time(self):
        r = SceneRegistry()
        scene = StubScene()
        r.register_singleton("boot", scene)
        assert r.get("boot") is r.get("boot")

    def test_overwrite_singleton(self):
        r = SceneRegistry()
        first = StubScene("first")
        second = StubScene("second")
        r.register_singleton("boot", first)
        r.register_singleton("boot", second)
        assert r.get("boot") is second


# ── register_factory ──────────────────────────────────────────

class TestRegisterFactory:
    def test_get_calls_factory(self):
        r = SceneRegistry()
        r.register_factory("title", lambda: StubScene("title"))
        scene = r.get("title")
        assert isinstance(scene, StubScene)
        assert scene.name == "title"

    def test_get_returns_fresh_instance_each_call(self):
        r = SceneRegistry()
        r.register_factory("title", lambda: StubScene())
        first = r.get("title")
        second = r.get("title")
        assert first is not second

    def test_factory_called_on_demand_not_at_registration(self):
        called = []
        def factory():
            called.append(True)
            return StubScene()

        r = SceneRegistry()
        r.register_factory("title", factory)
        assert len(called) == 0   # not called yet
        r.get("title")
        assert len(called) == 1   # called only on get()


# ── get ───────────────────────────────────────────────────────

class TestGet:
    def test_raises_key_error_for_missing_scene(self):
        r = SceneRegistry()
        with pytest.raises(KeyError):
            r.get("nonexistent")

    def test_key_error_message_contains_name(self):
        r = SceneRegistry()
        with pytest.raises(KeyError, match="nonexistent"):
            r.get("nonexistent")

    def test_singleton_takes_priority_over_factory(self):
        r = SceneRegistry()
        singleton = StubScene("singleton")
        r.register_singleton("scene", singleton)
        r.register_factory("scene", lambda: StubScene("factory"))
        assert r.get("scene") is singleton

    def test_multiple_scenes_independent(self):
        r = SceneRegistry()
        boot = StubScene("boot")
        r.register_singleton("boot", boot)
        r.register_factory("title", lambda: StubScene("title"))
        assert r.get("boot") is boot
        assert r.get("title").name == "title"