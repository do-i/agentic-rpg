# engine/shop/magic_core_shop_scene.py
#
# Phase 6 — Shop + Apothecary

from __future__ import annotations

import pygame
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.quantity_picker import QuantityPicker
from engine.common.scroll_list import ScrollListState
from engine.party.repository_state import RepositoryState
from engine.shop.magic_core_shop_renderer import MagicCoreShopRenderer
from engine.shop.shop_constants import (
    STATE_CONFIRM, STATE_LIST, STATE_POPUP, STATE_QTY,
)
from engine.shop.shop_scene_mixin import ShopSceneMixin

# Confirm dialog threshold — rates at or above this trigger confirmation
LARGE_RATE_THRESHOLD = 1_000

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 10


class MagicCoreShopScene(ShopSceneMixin, Scene):
    """
    Lets the player exchange Magic Cores for GP.

    States:
      list     — browsing available MC sizes
      qty      — selecting quantity for chosen size
      confirm  — confirmation dialog for L / XL (if enabled)
      toast    — brief "Exchanged!" message before auto-close
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        mc_sizes: list[tuple[str, str, int]],
        confirm_large: bool,
        *,
        sfx_manager,
    ) -> None:
        self._holder       = holder
        self._scene_manager = scene_manager
        self._registry     = registry
        self._on_close     = on_close
        self._mc_sizes     = mc_sizes
        self._confirm_large = confirm_large
        self._sfx_manager  = sfx_manager

        self._state        = STATE_LIST   # list | qty | confirm | popup
        # wrap-around cursor; the MC list is short and never scrolls
        self._list         = ScrollListState(max(len(mc_sizes), 1), wrap=True)
        self._picker       = QuantityPicker(QTY_STEP_SMALL, QTY_STEP_LARGE, loop=True)
        self._popup_text   = ""
        self._renderer     = MagicCoreShopRenderer()

    # ── Data helpers ──────────────────────────────────────────

    def _repo(self) -> RepositoryState:
        return self._holder.get().repository

    def _available(self) -> list[tuple[str, str, int, int]]:
        """Returns list of (item_id, label, rate, qty) for owned MC sizes."""
        repo = self._repo()
        result = []
        for item_id, label, rate in self._mc_sizes:
            entry = repo.get_item(item_id)
            if entry and entry.qty > 0:
                result.append((item_id, label, rate, entry.qty))
        return result

    def _selected(self) -> tuple[str, str, int, int] | None:
        return self._list.selected(self._available())

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == STATE_POPUP:
                self._handle_popup(event.key)
                return
            if self._state == STATE_LIST:
                self._handle_list(event.key)
            elif self._state == STATE_QTY:
                self._handle_qty(event.key)
            elif self._state == STATE_CONFIRM:
                self._handle_confirm(event.key)

    def _after_popup_dismiss(self) -> None:
        # Everything may have been exchanged — close instead of showing
        # an empty list.
        if self._available():
            self._state = STATE_LIST
        else:
            self._on_close()

    def _handle_list(self, key: int) -> None:
        avail = self._available()
        if not avail:
            if key == pygame.K_ESCAPE:
                self._close_shop()
            return

        if self._nav_list(key, len(avail)):
            return
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._play("confirm")
            self._picker.reset()
            self._state = STATE_QTY
        elif key == pygame.K_ESCAPE:
            self._close_shop()

    def _handle_qty(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = STATE_LIST
            return
        _, _, _, max_qty = sel

        if key == pygame.K_ESCAPE:
            self._play("cancel")
            self._state = STATE_LIST
        elif key == pygame.K_LEFT:
            self._picker.decrease_small(max_qty)
            self._play("hover")
        elif key == pygame.K_RIGHT:
            self._picker.increase_small(max_qty)
            self._play("hover")
        elif key == pygame.K_UP:
            self._picker.decrease_large(max_qty)
            self._play("hover")
        elif key == pygame.K_DOWN:
            self._picker.increase_large(max_qty)
            self._play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            _, _, rate, _ = sel
            self._play("confirm")
            if self._confirm_large and rate >= LARGE_RATE_THRESHOLD:
                self._state = STATE_CONFIRM
            else:
                self._do_exchange()

    def _handle_confirm(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_y):
            self._play("confirm")
            self._do_exchange()
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            self._play("cancel")
            self._state = STATE_QTY

    # ── Exchange ──────────────────────────────────────────────

    def _do_exchange(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id, label, rate, max_qty = sel
        qty   = min(self._picker.qty, max_qty)
        total = qty * rate

        repo = self._repo()
        entry = repo.get_item(item_id)
        if entry is None or entry.qty < qty:
            return

        repo.remove_item(item_id, qty)
        repo.add_gp(total)

        self._popup_text  = f"Exchanged {qty} x {label}    +{total:,} GP"
        self._state       = STATE_POPUP
        self._list.clamp(len(self._available()))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen,
            state=self._state,
            avail=self._available(),
            list_sel=self._list.selection,
            qty=self._picker.qty,
            popup_text=self._popup_text,
            gp=self._repo().gp,
            selected=self._selected(),
        )
