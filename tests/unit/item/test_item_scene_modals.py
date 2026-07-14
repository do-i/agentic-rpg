# tests/unit/item/test_item_scene_modals.py
#
# Modal dispatch coverage for ItemScene: action / discard / AOE confirm /
# tag editing / manage / target overlay flows and the per-event handler
# resolution (a handler may switch or close the modal mid-batch).

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from engine.common.font_provider import init_fonts
from engine.common.game_state import GameState
from engine.common.game_state_holder import GameStateHolder
from engine.item.item_scene import (
    ItemScene, M_ACTION, M_AOE, M_DISCARD, M_MANAGE, M_NEWTAG, M_TAGS,
    PAGE_LIST,
)


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


def _keys(*keys: int) -> list[pygame.event.Event]:
    return [
        pygame.event.Event(pygame.KEYDOWN, {
            "key": key, "mod": 0, "unicode": "", "scancode": 0,
        })
        for key in keys
    ]


def _text(text: str) -> list[pygame.event.Event]:
    return [pygame.event.Event(pygame.TEXTINPUT, {"text": text})]


def _make_scene(target: str = "single", items: dict[str, int] | None = None):
    holder = GameStateHolder()
    state = GameState()
    member = MagicMock()
    state.party.add_member(member)
    for item_id, qty in (items or {"herb": 3}).items():
        state.repository.add_item(item_id, qty)
    holder.set(state)

    effect_handler = MagicMock()
    effect_handler.is_field_usable.return_value = True
    effect_handler.get_def.return_value = MagicMock(target=target)
    effect_handler.valid_targets.return_value = [member]
    effect_handler.apply.return_value = MagicMock(warning="")

    scene = ItemScene(
        holder,
        scene_manager=MagicMock(),
        registry=MagicMock(),
        effect_handler=effect_handler,
        mc_catalog=None,
        use_aoe_confirm=True,
        return_scene_name="world_map",
        sfx_manager=MagicMock(),
    )
    # POUCH -> LIST ("All" tab).
    scene.handle_events(_keys(pygame.K_RETURN))
    assert scene.page_id == PAGE_LIST
    return scene, state, effect_handler


class TestActionModal:
    def test_enter_opens_action_modal(self):
        scene, _, _ = _make_scene()
        scene.handle_events(_keys(pygame.K_RETURN))
        assert scene._modal == M_ACTION

    def test_escape_closes_action_modal(self):
        scene, _, _ = _make_scene()
        scene.handle_events(_keys(pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_ESCAPE))
        assert scene._modal is None
        assert scene.page_id == PAGE_LIST

    def test_events_after_mid_batch_close_are_swallowed(self):
        scene, _, _ = _make_scene()
        scene.handle_events(_keys(pygame.K_RETURN))
        # ESC closes the modal; the trailing ENTER in the same batch must not
        # reach the list page (which would reopen the modal).
        scene.handle_events(_keys(pygame.K_ESCAPE, pygame.K_RETURN))
        assert scene._modal is None


class TestDiscardFlow:
    def test_action_to_discard_transition(self):
        scene, _, _ = _make_scene()
        scene.handle_events(_keys(pygame.K_RETURN))
        # Options: Use / Discard / Edit Tags.
        scene.handle_events(_keys(pygame.K_DOWN, pygame.K_RETURN))
        assert scene._modal == M_DISCARD

    def test_discard_commit_removes_items(self):
        scene, state, _ = _make_scene(items={"herb": 3})
        scene.handle_events(_keys(pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_DOWN, pygame.K_RETURN))
        # qty 1 -> 2, then confirm.
        scene.handle_events(_keys(pygame.K_RIGHT, pygame.K_RETURN))
        assert state.repository.get_item("herb").qty == 1
        assert scene._modal is None

    def test_discard_escape_returns_to_action(self):
        scene, _, _ = _make_scene()
        scene.handle_events(_keys(pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_DOWN, pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_ESCAPE))
        assert scene._modal == M_ACTION


class TestUseFlows:
    def test_single_target_use_opens_overlay_and_applies(self):
        scene, _, handler = _make_scene(target="single")
        scene.handle_events(_keys(pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_RETURN))       # "Use"
        assert scene._target_overlay is not None
        # Blocked input routes to the overlay; ENTER confirms first target.
        scene.handle_events(_keys(pygame.K_RETURN))
        handler.apply.assert_called_once()
        assert scene._target_overlay is None
        assert scene._modal is None

    def test_aoe_use_asks_for_confirm_then_applies(self):
        scene, _, handler = _make_scene(target="all_alive")
        scene.handle_events(_keys(pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_RETURN))       # "Use"
        assert scene._modal == M_AOE
        scene.handle_events(_keys(pygame.K_RETURN))
        handler.apply.assert_called_once()
        assert scene._modal is None

    def test_aoe_cancel_returns_to_action(self):
        scene, _, handler = _make_scene(target="all_alive")
        scene.handle_events(_keys(pygame.K_RETURN))
        scene.handle_events(_keys(pygame.K_RETURN))       # "Use"
        assert scene._modal == M_AOE
        scene.handle_events(_keys(pygame.K_n))
        assert scene._modal == M_ACTION
        handler.apply.assert_not_called()


class TestManageModal:
    def test_m_opens_manage_and_toggles_hidden(self):
        scene, state, _ = _make_scene(items={"herb": 1})
        scene.handle_events(_keys(pygame.K_m))
        assert scene._modal == M_MANAGE
        scene.handle_events(_keys(pygame.K_RETURN))
        assert state.repository.is_hidden("herb")
        scene.handle_events(_keys(pygame.K_ESCAPE))
        assert scene._modal is None


class TestTagEditing:
    def _open_tags(self, scene):
        scene.handle_events(_keys(pygame.K_RETURN))            # action modal
        scene.handle_events(_keys(pygame.K_DOWN, pygame.K_DOWN,
                                  pygame.K_RETURN))            # "Edit Tags"
        assert scene._modal == M_TAGS

    def test_toggle_system_tag(self):
        scene, state, _ = _make_scene(items={"herb": 1})
        self._open_tags(scene)
        scene.handle_events(_keys(pygame.K_RETURN))            # first row: "rare"
        assert "rare" in state.repository.get_item("herb").tags
        scene.handle_events(_keys(pygame.K_RETURN))            # toggle off
        assert "rare" not in state.repository.get_item("herb").tags

    def test_new_tag_text_input_commits(self):
        scene, state, _ = _make_scene(items={"herb": 1})
        self._open_tags(scene)
        scene.handle_events(_keys(pygame.K_UP))                # ensure top
        # Move to the trailing "(new)" row: 3 system rows, no custom tags.
        scene.handle_events(_keys(pygame.K_DOWN, pygame.K_DOWN, pygame.K_DOWN))
        scene.handle_events(_keys(pygame.K_RETURN))
        assert scene._modal == M_NEWTAG
        scene.handle_events(_text("loot"))
        scene.handle_events(_keys(pygame.K_RETURN))
        assert "loot" in state.repository.get_item("herb").tags
        assert scene._modal == M_TAGS

    def test_newtag_swallows_plain_keydown(self):
        scene, _, _ = _make_scene(items={"herb": 1})
        self._open_tags(scene)
        scene.handle_events(_keys(pygame.K_DOWN, pygame.K_DOWN, pygame.K_DOWN))
        scene.handle_events(_keys(pygame.K_RETURN))
        assert scene._modal == M_NEWTAG
        # Arbitrary non-text keydown must neither crash nor leak to the list.
        scene.handle_events(_keys(pygame.K_DOWN))
        assert scene._modal == M_NEWTAG
        scene.handle_events(_keys(pygame.K_ESCAPE))
        assert scene._modal == M_TAGS
