# tests/unit/core/scenes/test_status_scene.py

import pytest
import pygame
from unittest.mock import MagicMock

from engine.status.status_scene import StatusScene
from engine.common.game_state_holder import GameStateHolder
from engine.common.game_state import GameState
from engine.party.member_state import MemberState
from engine.party.party_state import PartyState
from engine.party.party_state import exp_pct
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
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

def make_all_members() -> list[MemberState]:
    return [
        make_member("Aric",  protagonist=True, class_name="Hero",
                    hp=68, hp_max=68, mp=40, mp_max=40,
                    level=8, exp=6200, exp_next=8944,
                    str_=18, dex=14, con=16, int_=9),
        make_member("Elise", class_name="Cleric",
                    hp=180, hp_max=180, mp=120, mp_max=140,
                    level=7, exp=4900, exp_next=6317,
                    str_=8, dex=10, con=14, int_=16,
                    equipped={"weapon": "Oak Staff", "body": "Robe Linen"}),
        make_member("Reiya", class_name="Sorcerer",
                    hp=11, hp_max=28, mp=48, mp_max=48,
                    level=8, exp=6080, exp_next=8497,
                    str_=6, dex=12, con=7, int_=20,
                    equipped={"weapon": "Oak Staff", "body": "Silk Robe"}),
        make_member("Jep",   class_name="Rogue",
                    hp=44, hp_max=44, mp=16, mp_max=16,
                    level=14, exp=17606, exp_next=21213,
                    str_=16, dex=26, con=13, int_=8,
                    equipped={"weapon": "Dagger", "shield": "Buckler"}),
        make_member("kael", "Kael", class_name="Warrior",
                    hp=128, hp_max=128, mp=0, mp_max=0,
                    str_=28, dex=14, con=26, int_=5,
                    level=20, exp=40000, exp_next=44721,
                    equipped={"weapon": "Iron Sword", "shield": "Iron Shield",
                              "body": "Chainmail"}),
    ]

def make_scene(members: list[MemberState] | None = None) -> tuple[StatusScene, GameStateHolder]:
    holder = GameStateHolder()
    state = GameState()
    for m in (members or [make_member(protagonist=True)]):
        state.party.add_member(m)
    holder.set(state)

    scene_manager = MagicMock(spec=SceneManager)
    registry = MagicMock(spec=SceneRegistry)
    scene = StatusScene(holder, scene_manager, registry, return_scene_name="world_map")
    return scene, holder


# ── Construction ──────────────────────────────────────────────

class TestStatusSceneInit:
    def test_selected_starts_at_zero(self):
        scene, _ = make_scene()
        assert scene._selected == 0

    def test_fonts_not_ready_on_init(self):
        scene, _ = make_scene()
        assert not scene._fonts_ready


# ── Navigation ────────────────────────────────────────────────

class TestNavigation:
    def _key(self, key):
        return [pygame.event.Event(pygame.KEYDOWN, {
            "key": key, "mod": 0, "unicode": "", "scancode": 0
        })]

    def test_down_moves_selection(self):
        members = [make_member("Aric"), make_member("Elise")]
        scene, _ = make_scene(members)
        scene.handle_events(self._key(pygame.K_DOWN))
        assert scene._selected == 1

    def test_up_does_not_go_below_zero(self):
        scene, _ = make_scene()
        scene.handle_events(self._key(pygame.K_UP))
        assert scene._selected == 0

    def test_down_does_not_exceed_last_member(self):
        members = [make_member("Aric"), make_member("Elise")]
        scene, _ = make_scene(members)
        scene._selected = 1
        scene.handle_events(self._key(pygame.K_DOWN))
        assert scene._selected == 1

    def test_s_key_closes(self):
        scene, _ = make_scene()
        scene_manager = scene._scene_manager
        scene.handle_events(self._key(pygame.K_s))
        scene_manager.switch.assert_called_once()

    def test_escape_closes(self):
        scene, _ = make_scene()
        scene_manager = scene._scene_manager
        scene.handle_events(self._key(pygame.K_ESCAPE))
        scene_manager.switch.assert_called_once()


# ── MemberState helpers ───────────────────────────────────────

class TestMemberState:
    def test_exp_pct_normal(self):
        m = make_member(exp=500, exp_next=1000)
        assert exp_pct(m) == 0.5

    def test_exp_pct_capped_at_one(self):
        m = make_member(exp=2000, exp_next=1000)
        assert exp_pct(m) == 1.0

    def test_exp_pct_zero_exp_next(self):
        m = make_member(exp=100, exp_next=0)
        assert exp_pct(m) == 1.0

    def test_equipped_slot_access(self):
        m = make_member()
        assert m.equipped.get("weapon") == "Iron Sword"
        assert m.equipped.get("accessory") is None

    def test_warrior_mp_max_zero(self):
        m = make_member(name="Kael", mp=0, mp_max=0)
        assert m.mp_max == 0


# ── Render (smoke test — no crash) ───────────────────────────

class TestRender:
    def test_render_does_not_crash_empty_party(self):
        scene, _ = make_scene([])
        screen = pygame.Surface((1280, 720))
        scene.render(screen)   # must not raise

    def test_render_does_not_crash_single_member(self):
        scene, _ = make_scene([make_member(protagonist=True)])
        screen = pygame.Surface((1280, 720))
        scene.render(screen)

    def test_render_does_not_crash_full_party(self):

        members = [
            make_member("Aric",  protagonist=True, class_name="Hero"),
            make_member("Elise", class_name="Cleric",   mp_max=140, hp=180, hp_max=180),
            make_member("Reiya", class_name="Sorcerer",  hp=11,  hp_max=28),
            make_member("Jep",   class_name="Rogue",     mp_max=16),
            make_member("Kael", class_name="Warrior",
                        hp=128, hp_max=128, mp=0, mp_max=0,
                        level=20, exp=40000, exp_next=44721),
        ]
        scene, _ = make_scene(members)
        screen = pygame.Surface((1280, 720))
        scene.render(screen)

    def test_fonts_ready_after_first_render(self):
        scene, _ = make_scene()
        screen = pygame.Surface((1280, 720))
        scene.render(screen)
        assert scene._fonts_ready
