# tests/unit/core/state/test_wizard_scene.py

from __future__ import annotations

import pygame
import pytest
from unittest.mock import MagicMock

from engine.common.wizard_scene import WizardPage, WizardScene


def keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


def make_pages_scene(
    *,
    counts: dict[str, int] | None = None,
    confirm: dict[str, str | None] | None = None,
    back: dict[str, str | None] | None = None,
    sfx=None,
):
    """Build a WizardScene with two pages 'a' and 'b'.

    Tests can override any subset; sensible defaults wire `a -> b` on confirm
    and `b -> a` on back, with `a -> close` on back.
    """
    from engine.audio.sfx_manager import SfxManager
    if sfx is None:
        sfx = SfxManager.null()
    counts = counts or {"a": 3, "b": 2}
    confirm = confirm or {"a": "b", "b": None}
    back = back or {"a": None, "b": "a"}
    scene_manager = MagicMock()
    registry = MagicMock()

    class _S(WizardScene):
        def render(self, screen):  # not exercised here
            pass

    scene = _S(scene_manager, registry, "exit_target", sfx)
    scene._register_page(WizardPage(
        name="a",
        count_fn=lambda: counts["a"],
        on_confirm=lambda: confirm["a"],
        on_back=lambda: back["a"],
    ))
    scene._register_page(WizardPage(
        name="b",
        count_fn=lambda: counts["b"],
        on_confirm=lambda: confirm["b"],
        on_back=lambda: back["b"],
    ))
    return scene, scene_manager, registry


# ── Page registration / lookup ───────────────────────────────

class TestPageRegistration:
    def test_first_registered_is_entry(self):
        scene, _, _ = make_pages_scene()
        assert scene.page_id == "a"

    def test_unknown_target_raises(self):
        scene, _, _ = make_pages_scene()
        with pytest.raises(KeyError, match="unknown wizard page"):
            scene._navigate("nope")


# ── Selection navigation ─────────────────────────────────────

class TestSelectionNav:
    def test_down_advances_selection(self):
        scene, _, _ = make_pages_scene()
        scene.handle_events([keydown(pygame.K_DOWN)])
        assert scene._page("a").selection == 1

    def test_up_clamps_at_zero(self):
        scene, _, _ = make_pages_scene()
        scene.handle_events([keydown(pygame.K_UP)])
        assert scene._page("a").selection == 0

    def test_down_clamps_at_count_minus_one(self):
        scene, _, _ = make_pages_scene(counts={"a": 2, "b": 2})
        for _ in range(10):
            scene.handle_events([keydown(pygame.K_DOWN)])
        assert scene._page("a").selection == 1

    def test_empty_page_no_op_on_up_down(self):
        scene, _, _ = make_pages_scene(counts={"a": 0, "b": 2})
        scene.handle_events([keydown(pygame.K_DOWN)])
        scene.handle_events([keydown(pygame.K_UP)])
        assert scene._page("a").selection == 0

    def test_hover_sfx_plays_on_change(self):
        sfx = MagicMock()
        scene, _, _ = make_pages_scene(sfx=sfx)
        scene.handle_events([keydown(pygame.K_DOWN)])
        assert ("hover",) in [c.args for c in sfx.play.call_args_list]

    def test_hover_sfx_silent_at_clamp(self):
        sfx = MagicMock()
        scene, _, _ = make_pages_scene(sfx=sfx)
        scene.handle_events([keydown(pygame.K_UP)])  # already at 0
        sfx.play.assert_not_called()


# ── ENTER / ESC navigation ───────────────────────────────────

class TestPageNavigation:
    def test_enter_advances_to_next_page(self):
        scene, _, _ = make_pages_scene()
        scene.handle_events([keydown(pygame.K_RETURN)])
        assert scene.page_id == "b"

    def test_enter_resets_target_page_selection(self):
        scene, _, _ = make_pages_scene()
        # Stash a non-zero selection on page b, then jump in.
        scene._page("b").selection = 1
        scene.handle_events([keydown(pygame.K_RETURN)])
        assert scene._page("b").selection == 0

    def test_enter_with_empty_page_is_no_op(self):
        scene, _, _ = make_pages_scene(counts={"a": 0, "b": 2})
        scene.handle_events([keydown(pygame.K_RETURN)])
        assert scene.page_id == "a"

    def test_enter_returning_none_stays_on_page(self):
        scene, _, _ = make_pages_scene(confirm={"a": None, "b": None})
        scene.handle_events([keydown(pygame.K_RETURN)])
        assert scene.page_id == "a"

    def test_escape_on_first_page_closes_scene(self):
        scene, scene_manager, registry = make_pages_scene()
        scene.handle_events([keydown(pygame.K_ESCAPE)])
        registry.get.assert_called_with("exit_target")
        scene_manager.switch.assert_called_once()

    def test_m_key_also_backs_out(self):
        scene, scene_manager, _ = make_pages_scene()
        scene.handle_events([keydown(pygame.K_m)])
        scene_manager.switch.assert_called_once()

    def test_escape_on_inner_page_returns_to_previous(self):
        scene, _, _ = make_pages_scene()
        scene.handle_events([keydown(pygame.K_RETURN)])  # a -> b
        scene.handle_events([keydown(pygame.K_ESCAPE)])  # b -> a
        assert scene.page_id == "a"


# ── Modal-overlay routing ────────────────────────────────────

class TestModalOverlayRouting:
    def test_blocked_input_swallows_events(self):
        sfx = MagicMock()

        class _Blocked(WizardScene):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self._blocked_calls = []
                self._register_page(WizardPage(
                    name="only",
                    count_fn=lambda: 5,
                    on_confirm=lambda: None,
                    on_back=lambda: None,
                ))

            def _is_input_blocked(self) -> bool:
                return True

            def _handle_blocked_input(self, events):
                self._blocked_calls.append(len(events))

            def render(self, screen):
                pass

        s = _Blocked(MagicMock(), MagicMock(), "x", sfx)
        s.handle_events([keydown(pygame.K_DOWN), keydown(pygame.K_RETURN)])
        # Wizard nav was bypassed entirely.
        assert s._page("only").selection == 0
        assert s._blocked_calls == [2]


# ── set_return_scene ─────────────────────────────────────────

class TestReturnScene:
    def test_set_return_scene_redirects_close(self):
        scene, scene_manager, registry = make_pages_scene()
        scene.set_return_scene("alt_target")
        scene.handle_events([keydown(pygame.K_ESCAPE)])
        registry.get.assert_called_with("alt_target")
