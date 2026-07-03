# tests/unit/scenes/test_item_shop_scene.py
#
# ItemShopScene logic: buy/sell flows, quantity caps, mode toggle.
# Rendering is exercised elsewhere; the renderer is mocked out.

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from engine.audio.sfx_manager import SfxManager
from engine.common.game_state_holder import GameStateHolder
from engine.party.repository_state import RepositoryState
from engine.shop.item_shop_scene import ItemShopScene, MODE_BUY, MODE_SELL


SHOP_ITEMS = [
    {"id": "potion", "name": "Potion", "buy_price": 50},
    {"id": "ether",  "name": "Ether",  "buy_price": 200},
    {"id": "elixir", "name": "Elixir", "buy_price": 1000,
     "unlock_flag": "shop_elixir_unlocked"},
]


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
    )
    return scene, repo, on_close


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
