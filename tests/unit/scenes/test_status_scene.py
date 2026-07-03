# tests/unit/scenes/test_status_scene.py

from __future__ import annotations

import pytest
import pygame
from unittest.mock import MagicMock

from engine.status.status_scene import (
    StatusScene, PAGE_MEMBER, PAGE_CATEGORY, PAGE_DETAIL, CAT_POSITION,
)
from engine.common.game_state_holder import GameStateHolder
from engine.common.game_state import GameState
from engine.party.member_state import MemberState
from engine.party.party_state import exp_pct
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.font_provider import init_fonts


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


def make_member(name="Aric", protagonist=False, hp=100, hp_max=100,
                mp=50, mp_max=80, level=5, exp=400, exp_next=1000,
                class_name="Hero") -> MemberState:
    return MemberState(
        member_id=name.lower(),
        name=name,
        protagonist=protagonist,
        class_name=class_name,
        level=level,
        exp=exp,
        exp_next=exp_next,
        hp=hp,
        hp_max=hp_max,
        mp=mp,
        mp_max=mp_max,
        str_=10, dex=8, con=9, int_=6,
        equipped={"weapon": "Iron Sword", "body": "Chainmail"},
    )


def make_scene(members: list[MemberState] | None = None) -> tuple[StatusScene, GameStateHolder]:
    holder = GameStateHolder()
    state = GameState()
    for m in (members or [make_member(protagonist=True)]):
        state.party.add_member(m)
    holder.set(state)

    scene_manager = MagicMock(spec=SceneManager)
    registry = MagicMock(spec=SceneRegistry)
    from engine.audio.sfx_manager import SfxManager
    scene = StatusScene(holder, scene_manager, registry, return_scene_name="world_map",
                        sfx_manager=SfxManager.null(), game_state_manager=MagicMock())
    return scene, holder


def _key(key):
    return [pygame.event.Event(pygame.KEYDOWN, {
        "key": key, "mod": 0, "unicode": "", "scancode": 0
    })]


# ── Construction ──────────────────────────────────────────────

class TestStatusSceneInit:
    def test_starts_on_member_page(self):
        scene, _ = make_scene()
        assert scene.page_id == PAGE_MEMBER
        assert scene._page(PAGE_MEMBER).selection == 0

    def test_fonts_lazy_on_init(self):
        # FontSet resolves on first access — construction needs no pygame font
        scene, _ = make_scene()
        assert scene._renderer._fonts._resolved is None


# ── Member navigation ─────────────────────────────────────────

class TestMemberNavigation:
    def test_down_moves_selection(self):
        scene, _ = make_scene([make_member("Aric"), make_member("Elise")])
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._page(PAGE_MEMBER).selection == 1

    def test_up_does_not_go_below_zero(self):
        scene, _ = make_scene()
        scene.handle_events(_key(pygame.K_UP))
        assert scene._page(PAGE_MEMBER).selection == 0

    def test_down_does_not_exceed_last_member(self):
        scene, _ = make_scene([make_member("Aric"), make_member("Elise")])
        scene._page(PAGE_MEMBER).selection = 1
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._page(PAGE_MEMBER).selection == 1

    def test_escape_closes_from_member_page(self):
        scene, _ = make_scene()
        scene.handle_events(_key(pygame.K_ESCAPE))
        scene._scene_manager.switch.assert_called_once()

    def test_enter_drills_into_category(self):
        scene, _ = make_scene()
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene.page_id == PAGE_CATEGORY


# ── Category → Position flow ──────────────────────────────────

class TestPositionFlow:
    def _drill_to_position_detail(self, scene):
        scene.handle_events(_key(pygame.K_RETURN))      # member -> category
        scene.handle_events(_key(pygame.K_DOWN))        # select Position (index 1)
        scene.handle_events(_key(pygame.K_RETURN))      # category -> detail

    def test_reaches_position_detail(self):
        scene, _ = make_scene()
        self._drill_to_position_detail(scene)
        assert scene.page_id == PAGE_DETAIL
        assert scene._detail_mode == CAT_POSITION

    def test_selecting_back_changes_row(self):
        scene, holder = make_scene()
        member = holder.get().party.members[0]
        assert member.row == "front"
        self._drill_to_position_detail(scene)
        scene.handle_events(_key(pygame.K_DOWN))        # select "Back"
        scene.handle_events(_key(pygame.K_RETURN))      # set row
        assert member.row == "back"

    def test_escape_backs_out_one_page(self):
        scene, _ = make_scene()
        scene.handle_events(_key(pygame.K_RETURN))      # member -> category
        scene.handle_events(_key(pygame.K_ESCAPE))      # category -> member
        assert scene.page_id == PAGE_MEMBER
        scene._scene_manager.switch.assert_not_called()


# ── MemberState helpers ───────────────────────────────────────

class TestMemberState:
    def test_exp_pct_normal(self):
        assert exp_pct(make_member(exp=500, exp_next=1000)) == 0.5

    def test_exp_pct_capped_at_one(self):
        assert exp_pct(make_member(exp=2000, exp_next=1000)) == 1.0

    def test_exp_pct_zero_exp_next(self):
        assert exp_pct(make_member(exp=100, exp_next=0)) == 1.0

    def test_warrior_mp_max_zero(self):
        assert make_member(name="Kael", mp=0, mp_max=0).mp_max == 0


# ── Render (smoke test — no crash) ───────────────────────────

class TestRender:
    def test_render_does_not_crash_empty_party(self):
        scene, _ = make_scene([])
        scene.render(pygame.Surface((1280, 766)))

    def test_render_does_not_crash_single_member(self):
        scene, _ = make_scene([make_member(protagonist=True)])
        scene.render(pygame.Surface((1280, 766)))

    def test_render_does_not_crash_full_party(self):
        members = [
            make_member("Aric",  protagonist=True, class_name="Hero"),
            make_member("Elise", class_name="Cleric",   mp_max=140, hp=180, hp_max=180),
            make_member("Reiya", class_name="Sorcerer",  hp=11,  hp_max=28),
            make_member("Jep",   class_name="Rogue",     mp_max=16),
            make_member("Kael",  class_name="Warrior",   mp=0, mp_max=0),
        ]
        scene, _ = make_scene(members)
        scene.render(pygame.Surface((1280, 766)))

    def test_render_detail_and_position_columns(self):
        scene, _ = make_scene()
        scene.render(pygame.Surface((1280, 766)))       # member portrait (renders col 2)
        scene.handle_events(_key(pygame.K_RETURN))      # category stats/actions
        scene.render(pygame.Surface((1280, 766)))
        scene.handle_events(_key(pygame.K_DOWN))        # Position
        scene.handle_events(_key(pygame.K_RETURN))      # detail (renders col 3)
        scene.render(pygame.Surface((1280, 766)))

    def test_fonts_resolved_after_first_render(self):
        scene, _ = make_scene()
        scene.render(pygame.Surface((1280, 766)))
        assert scene._renderer._fonts._resolved is not None
