# tests/unit/core/battle/test_game_over_scene.py

from __future__ import annotations

import pytest
import pygame
from unittest.mock import MagicMock

from engine.battle.game_over_scene import GameOverScene, MENU_ITEMS
from engine.common.font_provider import init_fonts
from engine.common.save_slot_data import SaveSlot


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


def make_scene(saves: bool = True, sfx=None) -> tuple[GameOverScene, MagicMock, MagicMock]:
    from engine.audio.sfx_manager import SfxManager
    if sfx is None:
        sfx = SfxManager.null()
    scene_manager = MagicMock()
    registry = MagicMock()
    holder = MagicMock()
    gsm = MagicMock()
    if saves:
        gsm.list_slots.return_value = [
            SaveSlot(slot_index=0, path="/x/000.yaml", is_autosave=True,
                     protagonist_name="Aric", level=2,
                     timestamp="2026-04-27 12:00:00",
                     playtime_display="0:01:00", location="town"),
        ]
    else:
        gsm.list_slots.return_value = [
            SaveSlot(slot_index=0, path=None, is_autosave=True),
        ]

    scene = GameOverScene(
        scene_manager=scene_manager,
        registry=registry,
        holder=holder,
        game_state_manager=gsm,
        sfx_manager=sfx,
    )
    # init_fonts runs lazily on first render — force it now so _has_saves
    # is populated for tests that don't render.
    scene._init_fonts()
    return scene, scene_manager, registry


def keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


# ── Initial state ─────────────────────────────────────────────

class TestInitialState:
    def test_with_saves_starts_on_load_game(self):
        scene, _, _ = make_scene(saves=True)
        assert scene._sel == 0  # Load Game
        assert scene._has_saves is True

    def test_without_saves_skips_load_game(self):
        scene, _, _ = make_scene(saves=False)
        assert scene._sel == 1  # Title Screen
        assert scene._has_saves is False


# ── Navigation ────────────────────────────────────────────────

class TestNavigation:
    def test_input_blocked_until_fade_done(self):
        scene, _, _ = make_scene()
        scene.handle_events([keydown(pygame.K_DOWN)])
        # _fade_done starts False; events are dropped.
        assert scene._sel == 0

    def test_down_advances_after_fade(self):
        scene, _, _ = make_scene()
        scene._fade_done = True
        scene.handle_events([keydown(pygame.K_DOWN)])
        assert scene._sel == 1

    def test_up_clamps_at_top(self):
        scene, _, _ = make_scene()
        scene._fade_done = True
        scene.handle_events([keydown(pygame.K_UP)])
        assert scene._sel == 0

    def test_up_skips_load_game_when_no_saves(self):
        scene, _, _ = make_scene(saves=False)
        scene._fade_done = True
        scene._sel = 2
        scene.handle_events([keydown(pygame.K_UP)])
        # Lands on Title Screen, not Load Game.
        assert scene._sel == 1

    def test_down_clamps_at_quit(self):
        scene, _, _ = make_scene()
        scene._fade_done = True
        scene._sel = len(MENU_ITEMS) - 1
        scene.handle_events([keydown(pygame.K_DOWN)])
        assert scene._sel == len(MENU_ITEMS) - 1

    def test_hover_sfx_plays_on_change(self):
        sfx = MagicMock()
        scene, _, _ = make_scene(sfx=sfx)
        scene._fade_done = True
        scene.handle_events([keydown(pygame.K_DOWN)])
        assert ("hover",) in [c.args for c in sfx.play.call_args_list]


# ── Confirm ───────────────────────────────────────────────────

class TestConfirm:
    def test_load_game_switches_to_load_scene(self):
        scene, scene_manager, registry = make_scene(saves=True)
        scene._fade_done = True
        scene._sel = 0  # Load Game
        scene.handle_events([keydown(pygame.K_RETURN)])
        registry.get.assert_called_with("load_game")
        scene_manager.switch.assert_called_once()

    def test_title_screen_switches_to_title(self):
        scene, scene_manager, registry = make_scene()
        scene._fade_done = True
        scene._sel = 1  # Title
        scene.handle_events([keydown(pygame.K_RETURN)])
        registry.get.assert_called_with("title")

    def test_quit_posts_quit_event(self):
        scene, _, _ = make_scene()
        scene._fade_done = True
        scene._sel = 2  # Quit
        # Pump and catch the QUIT post.
        pygame.event.clear()
        scene.handle_events([keydown(pygame.K_RETURN)])
        events = pygame.event.get()
        assert any(e.type == pygame.QUIT for e in events)

    def test_load_game_no_op_when_no_saves(self):
        scene, scene_manager, _ = make_scene(saves=False)
        scene._fade_done = True
        scene._sel = 0  # Load Game (disabled)
        scene.handle_events([keydown(pygame.K_RETURN)])
        scene_manager.switch.assert_not_called()


# ── Fade animation ────────────────────────────────────────────

class TestFadeAnimation:
    def test_fade_progresses_with_delta(self):
        scene, _, _ = make_scene()
        scene.update(0.5)
        assert 0 < scene._fade_alpha < 255

    def test_fade_completes(self):
        scene, _, _ = make_scene()
        scene.update(5.0)  # well past 255/200
        assert scene._fade_done is True
        assert scene._fade_alpha == 255

    def test_post_complete_update_no_op(self):
        scene, _, _ = make_scene()
        scene.update(5.0)
        scene.update(0.5)
        assert scene._fade_alpha == 255


# ── Render smoke ──────────────────────────────────────────────

class TestRender:
    def test_renders_with_saves(self):
        scene, _, _ = make_scene(saves=True)
        screen = pygame.Surface((640, 480))
        scene.render(screen)

    def test_renders_without_saves(self):
        scene, _, _ = make_scene(saves=False)
        screen = pygame.Surface((640, 480))
        scene.render(screen)

    def test_renders_post_fade(self):
        scene, _, _ = make_scene()
        scene._fade_done = True
        scene._fade_alpha = 255
        screen = pygame.Surface((640, 480))
        scene.render(screen)
