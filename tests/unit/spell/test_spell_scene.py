# tests/unit/core/spell/test_spell_scene.py

from __future__ import annotations

import pytest
import pygame
from unittest.mock import MagicMock

from engine.common.game_state import GameState
from engine.common.game_state_holder import GameStateHolder
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.font_provider import init_fonts
from engine.party.member_state import MemberState
from engine.spell.spell_scene import SpellScene, PAGE_MEMBER, PAGE_SPELL
from engine.audio.sfx_manager import SfxManager
from engine.world.position_data import Position
from engine.world.sprite_sheet import Direction


CLERIC_YAML = """\
abilities:
  - id: heal
    name: Heal
    type: heal
    unlock_level: 1
    mp_cost: 4
    heal_coeff: 2.0
    target: single_ally
  - id: heal_all
    name: Heal All
    type: heal
    unlock_level: 1
    mp_cost: 10
    heal_coeff: 1.5
    target: all_allies
  - id: aqua_shot
    name: Aqua Shot
    type: spell
    element: water
    unlock_level: 1
    mp_cost: 4
    spell_coeff: 1.0
    target: single_enemy
"""


@pytest.fixture(autouse=True)
def pygame_env():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


def _key(key: int) -> list[pygame.event.Event]:
    return [pygame.event.Event(pygame.KEYDOWN, {
        "key": key, "mod": 0, "unicode": "", "scancode": 0,
    })]


def make_member(name="Vela", level=5, mp=50, hp=60, class_name="cleric") -> MemberState:
    return MemberState(
        member_id=name.lower(), name=name, protagonist=False,
        class_name=class_name, level=level, exp=0, exp_next=100,
        hp=hp, hp_max=100, mp=mp, mp_max=50,
        str_=5, dex=5, con=5, int_=15, equipped={},
    )


def make_scene(tmp_path, members=None, flags=None):
    classes_dir = tmp_path / "data" / "classes"
    classes_dir.mkdir(parents=True)
    (classes_dir / "cleric.yaml").write_text(CLERIC_YAML)

    state = GameState()
    for m in (members or [make_member()]):
        state.party.add_member(m)
    for flag in (flags or []):
        state.flags.add_flag(flag)
    holder = GameStateHolder()
    holder.set(state)

    scene_manager = MagicMock(spec=SceneManager)
    registry = MagicMock(spec=SceneRegistry)
    scene = SpellScene(
        holder=holder,
        scene_manager=scene_manager,
        registry=registry,
        scenario_path=str(tmp_path),
        return_scene_name="world_map",
        sfx_manager=SfxManager.null(),
        game_state_manager=MagicMock(),
    )
    return scene, state, scene_manager, registry


class TestMemberPage:
    def test_escape_returns_to_world_map(self, tmp_path):
        scene, _, scene_manager, registry = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_ESCAPE))
        registry.get.assert_called_once_with("world_map")
        scene_manager.switch.assert_called_once()

    def test_m_also_closes(self, tmp_path):
        scene, _, scene_manager, registry = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_m))
        registry.get.assert_called_once_with("world_map")

    def test_enter_opens_spell_page_when_spells_exist(self, tmp_path):
        scene, *_ = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene.page_id == PAGE_SPELL
        assert len(scene._spells) == 3   # heal, heal_all, aqua_shot

    def test_enter_shows_popup_when_no_spells(self, tmp_path):
        # Warrior has no casting abilities in this fake yaml.
        warrior_member = make_member(class_name="warrior")
        # Write an empty abilities warrior yaml.
        classes_dir = tmp_path / "data" / "classes"
        classes_dir.mkdir(parents=True)
        (classes_dir / "warrior.yaml").write_text("abilities: []\n")
        # Build scene with just warrior.
        state = GameState()
        state.party.add_member(warrior_member)
        holder = GameStateHolder()
        holder.set(state)
        scene = SpellScene(
            holder=holder,
            scene_manager=MagicMock(spec=SceneManager),
            registry=MagicMock(spec=SceneRegistry),
            scenario_path=str(tmp_path),
            return_scene_name="world_map",
            sfx_manager=SfxManager.null(),
            game_state_manager=MagicMock(),
        )
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._popup_active
        assert scene.page_id == PAGE_MEMBER

    def test_down_moves_selection(self, tmp_path):
        m1 = make_member("A")
        m2 = make_member("B")
        scene, *_ = make_scene(tmp_path, members=[m1, m2])
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._page(PAGE_MEMBER).selection == 1


class TestSpellPage:
    def test_escape_returns_to_member_page(self, tmp_path):
        scene, *_ = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene.page_id == PAGE_SPELL
        scene.handle_events(_key(pygame.K_ESCAPE))
        assert scene.page_id == PAGE_MEMBER

    def test_enter_on_offensive_spell_is_blocked(self, tmp_path):
        scene, state, *_ = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_RETURN))  # open spell page
        # Spell list order: heal, heal_all, aqua_shot (battle-only at index 2)
        scene._page(PAGE_SPELL).selection = 2
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._target_overlay is None
        assert not scene._popup_active  # not an error, just a beep

    def test_enter_on_all_allies_heal_casts_immediately(self, tmp_path):
        m1 = make_member("A", mp=50, hp=40)
        m2 = make_member("B", mp=50, hp=30)
        scene, state, *_ = make_scene(tmp_path, members=[m1, m2])
        scene.handle_events(_key(pygame.K_RETURN))  # open spell page
        scene._page(PAGE_SPELL).selection = 1                          # heal_all
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._popup_active
        # MP deducted from active caster (member 0)
        assert m1.mp == 40
        # Both allies healed
        assert m1.hp > 40 and m2.hp > 30

    def test_enter_on_single_ally_opens_target_overlay(self, tmp_path):
        scene, *_ = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_RETURN))  # open spell page
        scene._page(PAGE_SPELL).selection = 0                          # heal (single_ally)
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._target_overlay is not None

    def test_insufficient_mp_blocks_cast(self, tmp_path):
        poor_caster = make_member(mp=0)
        scene, state, *_ = make_scene(tmp_path, members=[poor_caster])
        scene.handle_events(_key(pygame.K_RETURN))  # open spell page
        scene._page(PAGE_SPELL).selection = 0                          # heal — cost 4 > mp 0
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene._popup_active
        assert "MP" in scene._popup_text
        assert scene._target_overlay is None


HERO_YAML = """\
abilities:
  - id: teleport
    name: Teleport
    type: utility
    unlock_level: 1
    unlock_flag: aric_teleport_unlocked
    mp_cost: 8
    target: self
    warp: select
"""


def _tmx_with_portals(portals) -> str:
    """Minimal TMX holding only a 'portals' object layer (target_map + tile)."""
    objs = ""
    for i, (target_map, (tx, ty)) in enumerate(portals):
        objs += (
            f'<object id="{i + 1}" x="0" y="0" width="8" height="8">'
            f'<properties>'
            f'<property name="target_map" value="{target_map}"/>'
            f'<property name="target_position_x" type="int" value="{tx}"/>'
            f'<property name="target_position_y" type="int" value="{ty}"/>'
            f'</properties></object>'
        )
    return f'<?xml version="1.0"?><map><objectgroup name="portals">{objs}</objectgroup></map>'


def _write_warp_scenario(tmp_path):
    """A tiny world: zone_forest <-> town_ardel, plus an interior shop.

    Landing for town_ardel is the zone entrance (27, 12), not the shop exit.
    """
    maps_assets = tmp_path / "assets" / "maps"
    maps_data = tmp_path / "data" / "maps"
    maps_assets.mkdir(parents=True)
    maps_data.mkdir(parents=True)

    (maps_assets / "zone_forest.tmx").write_text(
        _tmx_with_portals([("town_ardel", (27, 12))]))
    (maps_assets / "town_ardel.tmx").write_text(
        _tmx_with_portals([("zone_forest", (5, 5)), ("town_ardel_shop", (3, 3))]))
    (maps_assets / "town_ardel_shop.tmx").write_text(
        _tmx_with_portals([("town_ardel", (9, 9))]))

    (maps_data / "zone_forest.yaml").write_text("name: Greenwood Forest\n")
    (maps_data / "town_ardel.yaml").write_text("name: Ardel Village\n")
    (maps_data / "town_ardel_shop.yaml").write_text("name: Ardel Shop\n")


def make_warp_scene(tmp_path):
    classes_dir = tmp_path / "data" / "classes"
    classes_dir.mkdir(parents=True)
    (classes_dir / "hero.yaml").write_text(HERO_YAML)
    _write_warp_scenario(tmp_path)

    state = GameState()
    state.party.add_member(make_member(name="Aric", class_name="hero"))
    state.flags.add_flag("aric_teleport_unlocked")
    # Standing in the forest, having visited the town (and its shop interior).
    state.map.move_to("town_ardel", Position(1, 1), Direction.DOWN)
    state.map.move_to("town_ardel_shop", Position(1, 1), Direction.DOWN)
    state.map.move_to("zone_forest", Position(1, 1), Direction.DOWN)
    holder = GameStateHolder()
    holder.set(state)

    gsm = MagicMock()
    scene = SpellScene(
        holder=holder,
        scene_manager=MagicMock(spec=SceneManager),
        registry=MagicMock(spec=SceneRegistry),
        scenario_path=str(tmp_path),
        return_scene_name="world_map",
        sfx_manager=SfxManager.null(),
        game_state_manager=gsm,
    )
    return scene, state, gsm


def _open_teleport(scene):
    scene.handle_events(_key(pygame.K_RETURN))   # open spell page
    scene._page(PAGE_SPELL).selection = 0        # teleport (only spell)
    scene.handle_events(_key(pygame.K_RETURN))   # cast → opens picker


class TestWarp:
    def test_teleport_unavailable_without_flag(self, tmp_path):
        # Same hero class, but the unlock flag is absent → spell not learned.
        classes_dir = tmp_path / "data" / "classes"
        classes_dir.mkdir(parents=True)
        (classes_dir / "hero.yaml").write_text(HERO_YAML)
        state = GameState()
        state.party.add_member(make_member(name="Aric", class_name="hero"))
        holder = GameStateHolder()
        holder.set(state)
        scene = SpellScene(
            holder=holder,
            scene_manager=MagicMock(spec=SceneManager),
            registry=MagicMock(spec=SceneRegistry),
            scenario_path=str(tmp_path),
            return_scene_name="world_map",
            sfx_manager=SfxManager.null(),
            game_state_manager=MagicMock(),
        )
        scene.handle_events(_key(pygame.K_RETURN))  # try open spell page
        assert scene.page_id == PAGE_MEMBER          # stayed: no learned spells
        assert scene._popup_active

    def test_teleport_opens_destination_picker(self, tmp_path):
        scene, state, gsm = make_warp_scene(tmp_path)
        _open_teleport(scene)
        assert scene._warp_overlay is not None
        # Only the top-level town is offered — current map and the shop
        # interior are excluded.
        dests = scene._warp_overlay._destinations
        assert [d.map_id for d in dests] == ["town_ardel"]
        gsm.save.assert_not_called()   # nothing committed until a pick

    def test_selecting_destination_warps_to_incoming_portal(self, tmp_path):
        scene, state, gsm = make_warp_scene(tmp_path)
        before_mp = scene._members()[0].mp
        _open_teleport(scene)
        scene.handle_events(_key(pygame.K_RETURN))   # confirm destination

        assert state.map.current == "town_ardel"
        assert (state.map.position.x, state.map.position.y) == (27, 12)
        assert scene._members()[0].mp == before_mp - 8
        assert scene._warp_overlay is None
        gsm.save.assert_called_once()
        scene._scene_manager.switch.assert_called_once()

    def test_cancel_picker_costs_nothing(self, tmp_path):
        scene, state, gsm = make_warp_scene(tmp_path)
        before_mp = scene._members()[0].mp
        _open_teleport(scene)
        scene.handle_events(_key(pygame.K_ESCAPE))   # back out of picker

        assert scene._warp_overlay is None
        assert state.map.current == "zone_forest"
        assert scene._members()[0].mp == before_mp
        gsm.save.assert_not_called()

    def test_teleport_blocked_without_mp(self, tmp_path):
        scene, state, gsm = make_warp_scene(tmp_path)
        scene._members()[0].mp = 0
        scene.handle_events(_key(pygame.K_RETURN))   # open spell page
        scene._page(PAGE_SPELL).selection = 0        # teleport
        scene.handle_events(_key(pygame.K_RETURN))   # try cast

        assert scene._warp_overlay is None
        assert state.map.current == "zone_forest"
        assert scene._popup_active
        gsm.save.assert_not_called()

    def test_no_visited_destinations_shows_popup(self, tmp_path):
        scene, state, gsm = make_warp_scene(tmp_path)
        # Wipe visited history: nowhere to go.
        state.map = state.map.__class__(current="zone_forest", position=Position(1, 1))
        scene.handle_events(_key(pygame.K_RETURN))   # open spell page
        scene._page(PAGE_SPELL).selection = 0
        scene.handle_events(_key(pygame.K_RETURN))   # cast

        assert scene._warp_overlay is None
        assert scene._popup_active
        gsm.save.assert_not_called()


class TestRender:
    def test_render_does_not_crash_on_member_page(self, tmp_path):
        scene, *_ = make_scene(tmp_path)
        screen = pygame.Surface((1280, 720))
        scene.render(screen)

    def test_render_does_not_crash_on_spell_page(self, tmp_path):
        scene, *_ = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_RETURN))
        screen = pygame.Surface((1280, 720))
        scene.render(screen)

    def test_render_with_target_overlay(self, tmp_path):
        scene, *_ = make_scene(tmp_path)
        scene.handle_events(_key(pygame.K_RETURN))
        scene._page(PAGE_SPELL).selection = 0  # heal
        scene.handle_events(_key(pygame.K_RETURN))
        screen = pygame.Surface((1280, 720))
        scene.render(screen)
