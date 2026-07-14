# tests/unit/shop/test_item_shop_scene.py
#
# ItemShopScene logic: buy/sell flows, quantity caps, mode toggle.
# Rendering is exercised elsewhere; the renderer is mocked out.

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from engine.audio.sfx_manager import SfxManager
from engine.common.font_provider import init_fonts
from engine.common.game_state_holder import GameStateHolder
from engine.item.item_catalog import ItemCatalog
from engine.party.member_state import MemberState
from engine.party.repository_state import RepositoryState
from engine.shop.item_shop_scene import ItemShopScene, MODE_BUY, MODE_SELL


SHOP_ITEMS = [
    {"id": "potion", "name": "Potion", "buy_price": 50},
    {"id": "ether",  "name": "Ether",  "buy_price": 200},
    {"id": "elixir", "name": "Elixir", "buy_price": 1000,
     "unlock_flag": "shop_elixir_unlocked"},
]


@pytest.fixture
def fonts():
    pygame.font.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})


def key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def make_scene(gp: int = 500):
    repo = RepositoryState(gp=gp)
    state = MagicMock()
    state.repository = repo
    state.flags.has_flag.return_value = False
    holder = MagicMock(spec=GameStateHolder)
    holder.get.return_value = state

    on_close = MagicMock()
    scene = ItemShopScene(
        holder=holder,
        scene_manager=MagicMock(),
        registry=MagicMock(),
        on_close=on_close,
        shop_items=SHOP_ITEMS,
        sprite_path=MagicMock(),
        sfx_manager=SfxManager.null(),
        item_catalog=MagicMock(),
        title="Item Shop",
    )
    return scene, repo, on_close


def make_equipment_scene(tmp_path, gp: int = 500):
    items_dir = tmp_path / "items"
    items_dir.mkdir()
    (items_dir / "weapons.yaml").write_text(
        "- id: iron_sword\n"
        "  name: Iron Sword\n"
        "  type: weapon\n"
        "  slot_category: sword\n"
        "  stats: {str: 4}\n"
        "  buy_price: 100\n"
        "  sell_price: 50\n"
    )
    catalog = ItemCatalog(items_dir)
    repo = RepositoryState(gp=gp, catalog=catalog)
    hero = _member("hero", "Aric", {"weapon": ["sword"]})
    mage = _member("mage", "Elise", {"weapon": ["staff"]})
    guard = _member("guard", "Kael", {"weapon": ["sword"]})
    scout = _member("scout", "Reiya", {"weapon": ["dagger"]})
    priest = _member("priest", "Jep", {"weapon": ["staff"]})
    state = MagicMock()
    state.repository = repo
    state.party.members = [hero, mage, guard, scout, priest]
    state.flags.has_flag.return_value = False
    holder = MagicMock(spec=GameStateHolder)
    holder.get.return_value = state

    scene = ItemShopScene(
        holder=holder,
        scene_manager=MagicMock(),
        registry=MagicMock(),
        on_close=MagicMock(),
        shop_items=[{"id": "iron_sword", "name": "Iron Sword", "buy_price": 100}],
        sprite_path=MagicMock(),
        sfx_manager=SfxManager.null(),
        item_catalog=catalog,
        title="Weapon Shop",
    )
    return scene, repo, hero, mage


def _member(member_id: str, name: str, equipment_slots: dict[str, list[str]]) -> MemberState:
    member = MemberState(
        member_id=member_id,
        name=name,
        protagonist=member_id == "hero",
        class_name=member_id,
        level=1,
        exp=0,
        hp=20,
        hp_max=20,
        mp=5,
        mp_max=5,
        str_=10,
        dex=8,
        con=9,
        int_=6,
        equipped={},
    )
    member.equipment_slots = equipment_slots
    return member


class TestBuyAvailability:
    def test_flag_locked_items_hidden(self):
        scene, _, _ = make_scene()
        assert [i["id"] for i in scene._buy_available()] == ["potion", "ether"]


class TestBuyFlow:
    def test_enter_opens_qty_then_buys(self):
        scene, repo, _ = make_scene(gp=500)
        scene.handle_events([key_event(pygame.K_RETURN)])   # potion -> qty
        assert scene._state == "qty"
        scene.handle_events([key_event(pygame.K_RIGHT)])    # qty 2
        scene.handle_events([key_event(pygame.K_RETURN)])   # buy
        assert scene._state == "popup"
        assert repo.gp == 400
        assert repo.get_item("potion").qty == 2

    def test_unaffordable_item_does_not_open_qty(self):
        scene, _, _ = make_scene(gp=10)
        scene.handle_events([key_event(pygame.K_RETURN)])
        assert scene._state == "list"

    def test_qty_capped_by_gp(self):
        scene, _, _ = make_scene(gp=120)                    # 2 potions max
        scene.handle_events([key_event(pygame.K_RETURN)])
        sel = scene._selected()
        assert scene._qty_max(sel) == 2

    def test_qty_large_step_clamps(self):
        scene, _, _ = make_scene(gp=500)                    # 10 potions by gp
        scene.handle_events([key_event(pygame.K_RETURN)])
        scene.handle_events([key_event(pygame.K_UP)])       # +5 -> 6
        assert scene._picker.qty == 6
        scene.handle_events([key_event(pygame.K_UP)])       # clamp at 10
        assert scene._picker.qty == 10


class TestEquipmentBuyFlow:
    def test_purchase_prompts_for_party_member_and_equips(self, tmp_path):
        scene, repo, hero, _ = make_equipment_scene(tmp_path, gp=500)
        scene.handle_events([key_event(pygame.K_RETURN)])   # qty
        scene.handle_events([key_event(pygame.K_RETURN)])   # buy, then equip prompt

        assert scene._state == "equip"
        assert repo.gp == 400
        assert repo.has_item("iron_sword")

        scene.handle_events([key_event(pygame.K_RETURN)])   # equip Aric
        assert scene._state == "popup"
        assert hero.equipped["weapon"] == "iron_sword"
        assert repo.has_item("iron_sword") is False

    def test_ineligible_party_member_cannot_equip_purchased_item(self, tmp_path):
        scene, repo, hero, mage = make_equipment_scene(tmp_path, gp=500)
        scene.handle_events([key_event(pygame.K_RETURN)])
        scene.handle_events([key_event(pygame.K_RETURN)])

        scene.handle_events([key_event(pygame.K_DOWN)])     # Elise cannot use swords
        scene.handle_events([key_event(pygame.K_RETURN)])
        assert scene._state == "equip"
        assert "weapon" not in mage.equipped
        assert repo.has_item("iron_sword")

        scene.handle_events([key_event(pygame.K_UP)])
        scene.handle_events([key_event(pygame.K_RETURN)])
        assert hero.equipped["weapon"] == "iron_sword"

    def test_escape_skips_optional_equip_prompt(self, tmp_path):
        scene, repo, hero, _ = make_equipment_scene(tmp_path, gp=500)
        scene.handle_events([key_event(pygame.K_RETURN)])
        scene.handle_events([key_event(pygame.K_RETURN)])
        scene.handle_events([key_event(pygame.K_ESCAPE)])

        assert scene._state == "popup"
        assert "weapon" not in hero.equipped
        assert repo.has_item("iron_sword")

    def test_equipment_shop_preview_render_smoke(self, tmp_path, fonts):
        scene, _, _, _ = make_equipment_scene(tmp_path, gp=500)
        scene._sprite_loaded = True
        scene._sprite_surf = None

        scene.render(pygame.Surface((1280, 720)))
        scene.handle_events([key_event(pygame.K_RETURN)])
        scene.handle_events([key_event(pygame.K_RETURN)])
        scene.render(pygame.Surface((1280, 720)))


class TestSellFlow:
    def _stock(self, repo: RepositoryState) -> None:
        entry = repo.add_item("herb", 3)
        entry.name = "Herb"
        entry.sellable = True
        entry.sell_price = 7

    def test_tab_toggles_mode(self):
        scene, repo, _ = make_scene()
        scene.handle_events([key_event(pygame.K_TAB)])
        assert scene._mode == MODE_SELL
        scene.handle_events([key_event(pygame.K_TAB)])
        assert scene._mode == MODE_BUY

    def test_sell_grants_gp(self):
        scene, repo, _ = make_scene(gp=0)
        self._stock(repo)
        scene.handle_events([key_event(pygame.K_TAB)])
        scene.handle_events([key_event(pygame.K_RETURN)])   # qty
        scene.handle_events([key_event(pygame.K_RIGHT)])    # 2
        scene.handle_events([key_event(pygame.K_RETURN)])   # sell
        assert repo.gp == 14
        assert repo.get_item("herb").qty == 1

    def test_sell_qty_capped_by_owned(self):
        scene, repo, _ = make_scene()
        self._stock(repo)
        scene.handle_events([key_event(pygame.K_TAB)])
        sel = scene._selected()
        assert scene._qty_max(sel) == 3


class TestNavigation:
    def test_arrow_moves_selection_and_esc_closes(self):
        scene, _, on_close = make_scene()
        scene.handle_events([key_event(pygame.K_DOWN)])
        assert scene._list.selection == 1
        scene.handle_events([key_event(pygame.K_ESCAPE)])
        on_close.assert_called_once()
