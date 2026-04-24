# tests/unit/core/scenes/test_field_menu_scene.py

import pytest
import pygame
from unittest.mock import MagicMock

from engine.field_menu.field_menu_scene import (
    FieldMenuScene,
    KIND_SCENE_SWITCH,
    KIND_OVERLAY,
    KIND_DISABLED,
)
from engine.common.game_state_holder import GameStateHolder
from engine.common.game_state import GameState
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.font_provider import init_fonts


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


def _key(key: int) -> list[pygame.event.Event]:
    return [pygame.event.Event(pygame.KEYDOWN, {
        "key": key, "mod": 0, "unicode": "", "scancode": 0
    })]


def make_scene():
    holder = GameStateHolder()
    holder.set(GameState())
    scene_manager = MagicMock(spec=SceneManager)
    registry = MagicMock(spec=SceneRegistry)
    game_state_manager = MagicMock()
    scene = FieldMenuScene(
        holder=holder,
        scene_manager=scene_manager,
        registry=registry,
        game_state_manager=game_state_manager,
        return_scene_name="world_map",
        sfx_manager=None,
    )
    return scene, holder, scene_manager, registry, game_state_manager


class TestEntries:
    def test_entry_list_has_expected_order(self):
        scene, *_ = make_scene()
        labels = [e.label for e in scene._entries]
        assert labels == ["Items", "Status", "Equipment", "Spells", "Save"]

    def test_items_status_equipment_spells_dispatch_by_scene_switch(self):
        scene, *_ = make_scene()
        kinds = {e.label: e.kind for e in scene._entries}
        assert kinds["Items"] == KIND_SCENE_SWITCH
        assert kinds["Status"] == KIND_SCENE_SWITCH
        assert kinds["Equipment"] == KIND_SCENE_SWITCH
        assert kinds["Spells"] == KIND_SCENE_SWITCH

    def test_save_is_overlay(self):
        scene, *_ = make_scene()
        kinds = {e.label: e.kind for e in scene._entries}
        assert kinds["Save"] == KIND_OVERLAY


class TestNavigation:
    def test_down_moves_selection(self):
        scene, *_ = make_scene()
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._selected == 1

    def test_down_wraps_to_top(self):
        scene, *_ = make_scene()
        scene._selected = len(scene._entries) - 1
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._selected == 0

    def test_up_wraps_to_bottom(self):
        scene, *_ = make_scene()
        scene._selected = 0
        scene.handle_events(_key(pygame.K_UP))
        assert scene._selected == len(scene._entries) - 1


class TestClose:
    def test_escape_returns_to_world_map(self):
        scene, _, scene_manager, registry, _ = make_scene()
        scene.handle_events(_key(pygame.K_ESCAPE))
        registry.get.assert_called_once_with("world_map")
        scene_manager.switch.assert_called_once()

    def test_m_closes_menu(self):
        scene, _, scene_manager, registry, _ = make_scene()
        scene.handle_events(_key(pygame.K_m))
        registry.get.assert_called_once_with("world_map")
        scene_manager.switch.assert_called_once()


class TestSelect:
    def test_items_switches_and_sets_return_scene(self):
        scene, _, scene_manager, registry, _ = make_scene()
        items_scene = MagicMock()
        registry.get.return_value = items_scene
        # Selected defaults to 0 (Items)
        scene.handle_events(_key(pygame.K_RETURN))
        registry.get.assert_called_once_with("items")
        items_scene.set_return_scene.assert_called_once_with("field_menu")
        scene_manager.switch.assert_called_once_with(items_scene)

    def test_status_switches_and_sets_return_scene(self):
        scene, _, scene_manager, registry, _ = make_scene()
        status_scene = MagicMock()
        registry.get.return_value = status_scene
        scene._selected = 1   # Status
        scene.handle_events(_key(pygame.K_RETURN))
        registry.get.assert_called_once_with("status")
        status_scene.set_return_scene.assert_called_once_with("field_menu")

    def test_scene_switch_tolerates_missing_setter(self):
        scene, _, scene_manager, registry, _ = make_scene()
        sub_scene = object()   # has no set_return_scene
        registry.get.return_value = sub_scene
        scene._selected = 0
        scene.handle_events(_key(pygame.K_RETURN))   # must not raise
        scene_manager.switch.assert_called_once_with(sub_scene)

    def test_spells_switches_to_spell_scene(self):
        scene, _, scene_manager, registry, _ = make_scene()
        spell_scene = MagicMock()
        registry.get.return_value = spell_scene
        scene._selected = 3   # Spells
        scene.handle_events(_key(pygame.K_RETURN))
        registry.get.assert_called_once_with("spells")
        spell_scene.set_return_scene.assert_called_once_with("field_menu")

    def test_equipment_switches_to_equip_scene(self):
        scene, _, scene_manager, registry, _ = make_scene()
        equip_scene = MagicMock()
        registry.get.return_value = equip_scene
        scene._selected = 2   # Equipment
        scene.handle_events(_key(pygame.K_RETURN))
        registry.get.assert_called_once_with("equip")
        equip_scene.set_return_scene.assert_called_once_with("field_menu")

    def test_save_opens_overlay(self):
        scene, *_ = make_scene()
        scene._selected = 4   # Save
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._save_modal is not None

    def test_save_overlay_captures_events(self):
        scene, *_ = make_scene()
        scene._selected = 4
        scene.handle_events(_key(pygame.K_RETURN))
        modal = scene._save_modal
        modal.handle_events = MagicMock()
        scene.handle_events(_key(pygame.K_DOWN))
        modal.handle_events.assert_called_once()

    def test_save_overlay_close_clears_modal(self):
        scene, *_ = make_scene()
        scene._selected = 4
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._save_modal is not None
        scene._close_save_modal()
        assert scene._save_modal is None


class TestRender:
    def test_render_does_not_crash(self):
        scene, *_ = make_scene()
        screen = pygame.Surface((1280, 720))
        scene.render(screen)   # must not raise

    def test_fonts_ready_after_first_render(self):
        scene, *_ = make_scene()
        screen = pygame.Surface((1280, 720))
        scene.render(screen)
        assert scene._fonts_ready
