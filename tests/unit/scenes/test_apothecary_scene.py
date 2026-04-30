# tests/unit/core/scenes/test_apothecary_scene.py

from __future__ import annotations

import pytest
import pygame
from unittest.mock import MagicMock

from engine.shop.apothecary_scene import ApothecaryScene
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


UNIQUE_RECIPE = {
    "id": "recipe_veil_breaker",
    "scroll_name": "Alchemist's Lens",
    "output": {"item": "veil_breaker", "qty": 1},
    "unique_output": True,
    "inputs": {"items": [{"id": "spirit_orb", "qty": 1}]},
    "gp_cost": 400,
    "unlock_flag": "story_act2_started",
}

PLAIN_RECIPE = {
    "id": "recipe_hi_potion",
    "scroll_name": "Vital Brew",
    "output": {"item": "hi_potion", "qty": 2},
    "inputs": {"items": [{"id": "herb_red", "qty": 2}]},
    "gp_cost": 180,
    "unlock_flag": "story_act2_started",
}


def _key(key: int) -> list[pygame.event.Event]:
    return [pygame.event.Event(pygame.KEYDOWN, {
        "key": key, "mod": 0, "unicode": "", "scancode": 0,
    })]


def _make_scene(recipes, flags=("story_act2_started",), owned=None, gp=10_000):
    holder = GameStateHolder()
    state = GameState()
    for flag in flags:
        state.flags.add_flag(flag)
    state.repository.add_gp(gp)
    for item_id, qty in (owned or {}).items():
        state.repository.add_item(item_id, qty)
    holder.set(state)

    scene = ApothecaryScene(
        holder=holder,
        scene_manager=MagicMock(spec=SceneManager),
        registry=MagicMock(spec=SceneRegistry),
        on_close=MagicMock(),
        recipes=list(recipes),
        sprite_path=None,
        sfx_manager=None,
    )
    return scene, holder


class TestIsDuplicateBlocked:
    def test_unique_and_owned_is_blocked(self):
        scene, _ = _make_scene([UNIQUE_RECIPE], owned={"veil_breaker": 1})
        assert scene._is_duplicate_blocked(UNIQUE_RECIPE) is True

    def test_unique_but_not_owned_is_allowed(self):
        scene, _ = _make_scene([UNIQUE_RECIPE], owned={})
        assert scene._is_duplicate_blocked(UNIQUE_RECIPE) is False

    def test_non_unique_recipe_is_never_blocked(self):
        scene, _ = _make_scene([PLAIN_RECIPE], owned={"hi_potion": 99})
        assert scene._is_duplicate_blocked(PLAIN_RECIPE) is False

    def test_missing_output_is_not_blocked(self):
        recipe = dict(UNIQUE_RECIPE, output={})
        scene, _ = _make_scene([recipe], owned={})
        assert scene._is_duplicate_blocked(recipe) is False


class TestCanCraft:
    def test_can_craft_blocked_when_duplicate_owned(self):
        scene, _ = _make_scene(
            [UNIQUE_RECIPE],
            owned={"veil_breaker": 1, "spirit_orb": 5},
        )
        assert scene._can_craft(UNIQUE_RECIPE) is False

    def test_can_craft_allowed_when_not_owned(self):
        scene, _ = _make_scene(
            [UNIQUE_RECIPE],
            owned={"spirit_orb": 5},
        )
        assert scene._can_craft(UNIQUE_RECIPE) is True


class TestEnterBlocksDetail:
    def test_enter_on_blocked_row_stays_in_list(self):
        scene, _ = _make_scene(
            [UNIQUE_RECIPE],
            owned={"veil_breaker": 1, "spirit_orb": 5},
        )
        assert scene._state == "list"
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._state == "list"

    def test_enter_on_unblocked_row_opens_detail(self):
        scene, _ = _make_scene(
            [UNIQUE_RECIPE],
            owned={"spirit_orb": 5},
        )
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._state == "detail"

    def test_enter_on_plain_recipe_opens_detail_even_if_output_owned(self):
        scene, _ = _make_scene(
            [PLAIN_RECIPE],
            owned={"hi_potion": 99, "herb_red": 5},
        )
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._state == "detail"


class TestCraftCannotDuplicate:
    def test_crafting_blocked_recipe_is_noop(self):
        scene, holder = _make_scene(
            [UNIQUE_RECIPE],
            owned={"veil_breaker": 1, "spirit_orb": 5},
            gp=10_000,
        )
        # Force into detail state to simulate would-be craft path; then ENTER
        # should NOT consume inputs because _can_craft returns False.
        scene._state = "detail"
        gp_before = holder.get().repository.gp
        scene.handle_events(_key(pygame.K_RETURN))
        assert holder.get().repository.gp == gp_before
        assert holder.get().repository.get_item("veil_breaker").qty == 1
        assert holder.get().repository.get_item("spirit_orb").qty == 5


class TestRender:
    def test_render_does_not_crash(self):
        scene, _ = _make_scene(
            [UNIQUE_RECIPE],
            owned={"veil_breaker": 1, "spirit_orb": 5},
        )
        screen = pygame.Surface((1280, 720))
        scene.render(screen)
