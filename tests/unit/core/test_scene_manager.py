# tests/unit/core/test_scene_manager.py

from engine.scenes.scene_manager import SceneManager
from engine.scenes.scene import Scene


class StubScene(Scene):
    def __init__(self):
        self.events_received = []
        self.updates = []
        self.renders = []

    def handle_events(self, events):
        self.events_received.extend(events)

    def update(self, delta):
        self.updates.append(delta)

    def render(self, screen):
        self.renders.append(screen)


class TestSceneManager:
    def test_switch_sets_current_scene(self):
        sm = SceneManager()
        scene = StubScene()
        sm.switch(scene)
        sm.handle_events(["evt"])
        assert scene.events_received == ["evt"]

    def test_handle_events_noop_without_scene(self):
        sm = SceneManager()
        sm.handle_events(["evt"])  # should not raise

    def test_update_delegates_to_current(self):
        sm = SceneManager()
        scene = StubScene()
        sm.switch(scene)
        sm.update(0.016)
        assert scene.updates == [0.016]

    def test_update_noop_without_scene(self):
        sm = SceneManager()
        sm.update(0.016)  # should not raise

    def test_render_delegates_to_current(self):
        sm = SceneManager()
        scene = StubScene()
        sm.switch(scene)
        sm.render("screen")
        assert scene.renders == ["screen"]

    def test_render_noop_without_scene(self):
        sm = SceneManager()
        sm.render("screen")  # should not raise

    def test_switch_replaces_scene(self):
        sm = SceneManager()
        s1 = StubScene()
        s2 = StubScene()
        sm.switch(s1)
        sm.switch(s2)
        sm.handle_events(["evt"])
        assert s1.events_received == []
        assert s2.events_received == ["evt"]
