# tests/unit/core/equipment/test_equip_scene.py

from __future__ import annotations

import pytest
import pygame
from unittest.mock import MagicMock

from engine.equipment.equip_scene import (
    EquipScene, SLOTS, PAGE_MEMBER, PAGE_SLOT, PAGE_PICKER,
)
from engine.common.game_state_holder import GameStateHolder
from engine.common.game_state import GameState
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.font_provider import init_fonts
from engine.item.item_catalog import ItemCatalog
from engine.party.member_state import MemberState


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


@pytest.fixture
def catalog(tmp_path):
    d = tmp_path / "items"
    d.mkdir()
    (d / "weapons.yaml").write_text(
        "- id: iron_sword\n"
        "  name: Iron Sword\n"
        "  type: weapon\n"
        "  slot_category: sword\n"
        "  stats: {str: 4}\n"
        "  buy_price: 350\n"
        "  sell_price: 175\n"
        "- id: steel_axe\n"
        "  name: Steel Axe\n"
        "  type: weapon\n"
        "  slot_category: axe\n"
        "  stats: {str: 5, dex: -1}\n"
        "  buy_price: 400\n"
        "  sell_price: 200\n"
    )
    return ItemCatalog(d)


def _key(key: int) -> list[pygame.event.Event]:
    return [pygame.event.Event(pygame.KEYDOWN, {
        "key": key, "mod": 0, "unicode": "", "scancode": 0,
    })]


def _make_member(name="Aric", class_name="hero", equipped=None):
    m = MemberState(
        member_id=name.lower(), name=name, protagonist=True,
        class_name=class_name, level=3, exp=0,
        hp=50, hp_max=50, mp=10, mp_max=10,
        str_=10, dex=8, con=9, int_=6,
        equipped=equipped if equipped is not None else {},
    )
    m.equipment_slots = {
        "weapon":    ["sword", "axe"],
        "shield":    ["all"],
        "helmet":    ["all"],
        "body":      ["all"],
        "accessory": ["all"],
    }
    return m


def _make_scene(catalog, members=None, inventory=None):
    holder = GameStateHolder()
    state = GameState()
    state.repository.catalog = catalog
    if members:
        for m in members:
            state.party.add_member(m)
    for item_id, qty in (inventory or {}).items():
        state.repository.add_item(item_id, qty)
    holder.set(state)

    scene = EquipScene(
        holder=holder,
        scene_manager=MagicMock(spec=SceneManager),
        registry=MagicMock(spec=SceneRegistry),
        catalog=catalog,
        return_scene_name="field_menu",
        sfx_manager=None,
    )
    return scene, holder


class TestInitialState:
    def test_starts_on_member_page(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        assert scene.page_id == PAGE_MEMBER
        assert scene._page(PAGE_MEMBER).selection == 0


class TestMemberPage:
    def test_down_moves_member_sel(self, catalog):
        scene, _ = _make_scene(catalog,
            members=[_make_member("A"), _make_member("B")])
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._page(PAGE_MEMBER).selection == 1

    def test_enter_advances_to_slot_page(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        scene.handle_events(_key(pygame.K_RETURN))
        assert scene.page_id == PAGE_SLOT
        assert scene._page(PAGE_SLOT).selection == 0

    def test_escape_returns_to_field_menu(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        scene.handle_events(_key(pygame.K_ESCAPE))
        scene._scene_manager.switch.assert_called_once()
        scene._registry.get.assert_called_once_with("field_menu")


class TestSlotPage:
    def test_escape_returns_to_member_page(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        scene.handle_events(_key(pygame.K_RETURN))   # -> SLOT
        scene.handle_events(_key(pygame.K_ESCAPE))
        assert scene.page_id == PAGE_MEMBER

    def test_down_moves_slot(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        scene.handle_events(_key(pygame.K_RETURN))   # -> SLOT
        scene.handle_events(_key(pygame.K_DOWN))
        assert scene._page(PAGE_SLOT).selection == 1

    def test_enter_opens_picker(self, catalog):
        scene, _ = _make_scene(catalog,
            members=[_make_member()],
            inventory={"iron_sword": 1})
        scene.handle_events(_key(pygame.K_RETURN))   # -> SLOT
        scene.handle_events(_key(pygame.K_RETURN))   # -> PICKER
        assert scene.page_id == PAGE_PICKER
        ids = [r.item_id for r in scene._picker_rows]
        assert None in ids   # Unequip row present
        assert "iron_sword" in ids


class TestPickerPage:
    def test_escape_returns_to_slot_page(self, catalog):
        scene, _ = _make_scene(catalog,
            members=[_make_member()],
            inventory={"iron_sword": 1})
        scene.handle_events(_key(pygame.K_RETURN))   # SLOT
        scene.handle_events(_key(pygame.K_RETURN))   # PICKER
        scene.handle_events(_key(pygame.K_ESCAPE))
        assert scene.page_id == PAGE_SLOT

    def test_select_item_equips_it(self, catalog):
        m = _make_member()
        scene, holder = _make_scene(catalog,
            members=[m], inventory={"iron_sword": 1})
        scene.handle_events(_key(pygame.K_RETURN))   # SLOT
        scene.handle_events(_key(pygame.K_RETURN))   # PICKER
        scene.handle_events(_key(pygame.K_DOWN))     # skip Unequip row
        scene.handle_events(_key(pygame.K_RETURN))   # equip
        assert m.equipped["weapon"] == "iron_sword"
        assert not holder.get().repository.has_item("iron_sword")
        assert scene.page_id == PAGE_SLOT

    def test_select_unequip_row_returns_item(self, catalog):
        m = _make_member(equipped={"weapon": "iron_sword"})
        scene, holder = _make_scene(catalog, members=[m])
        scene.handle_events(_key(pygame.K_RETURN))   # SLOT
        scene.handle_events(_key(pygame.K_RETURN))   # PICKER
        # item_sel = 0 is the Unequip row
        scene.handle_events(_key(pygame.K_RETURN))
        assert m.equipped["weapon"] == ""
        assert holder.get().repository.has_item("iron_sword")
        assert scene.page_id == PAGE_SLOT

    def test_swap_returns_previous_to_repo(self, catalog):
        m = _make_member(equipped={"weapon": "iron_sword"})
        scene, holder = _make_scene(catalog,
            members=[m], inventory={"steel_axe": 1})
        scene.handle_events(_key(pygame.K_RETURN))   # SLOT
        scene.handle_events(_key(pygame.K_RETURN))   # PICKER
        scene.handle_events(_key(pygame.K_DOWN))     # skip Unequip
        scene.handle_events(_key(pygame.K_RETURN))   # equip steel_axe
        assert m.equipped["weapon"] == "steel_axe"
        repo = holder.get().repository
        assert repo.has_item("iron_sword")
        assert not repo.has_item("steel_axe")


class TestRender:
    def test_member_page_render_no_crash(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        scene.render(pygame.Surface((1280, 720)))

    def test_slot_page_render_no_crash(self, catalog):
        scene, _ = _make_scene(catalog, members=[_make_member()])
        scene.handle_events(_key(pygame.K_RETURN))
        scene.render(pygame.Surface((1280, 720)))

    def test_picker_page_render_no_crash(self, catalog):
        scene, _ = _make_scene(catalog,
            members=[_make_member()],
            inventory={"iron_sword": 1})
        scene.handle_events(_key(pygame.K_RETURN))
        scene.handle_events(_key(pygame.K_RETURN))
        scene.render(pygame.Surface((1280, 720)))
