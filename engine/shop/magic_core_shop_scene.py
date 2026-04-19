# engine/shop/magic_core_shop_scene.py
#
# Phase 6 — Shop + Apothecary

from __future__ import annotations

import pygame
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.party.repository_state import RepositoryState
from engine.shop.magic_core_shop_renderer import MagicCoreShopRenderer

# Confirm dialog threshold — rates at or above this trigger confirmation
LARGE_RATE_THRESHOLD = 1_000

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 10


class MagicCoreShopScene(Scene):
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
        confirm_large: bool = True,
        return_scene_name: str = "world_map",
        sfx_manager=None,
    ) -> None:
        self._holder       = holder
        self._scene_manager = scene_manager
        self._registry     = registry
        self._on_close     = on_close
        self._mc_sizes     = mc_sizes
        self._confirm_large = confirm_large
        self._return_scene_name = return_scene_name
        self._sfx_manager  = sfx_manager

        self._state        = "list"   # list | qty | confirm | popup
        self._list_sel     = 0        # index into _available()
        self._qty          = 1
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
        avail = self._available()
        if not avail:
            return None
        idx = min(self._list_sel, len(avail) - 1)
        return avail[idx]

    def _clamp_list_sel(self) -> None:
        avail = self._available()
        if avail:
            self._list_sel = max(0, min(self._list_sel, len(avail) - 1))

    def _qty_loop(self, delta: int, max_qty: int) -> None:
        """Adjust quantity with looping."""
        self._qty += delta
        if self._qty < 1:
            self._qty = max_qty
        elif self._qty > max_qty:
            self._qty = 1

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "popup":
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    avail = self._available()
                    if avail:
                        self._state = "list"
                    else:
                        self._on_close()
                return
            if self._state == "list":
                self._handle_list(event.key)
            elif self._state == "qty":
                self._handle_qty(event.key)
            elif self._state == "confirm":
                self._handle_confirm(event.key)

    def _handle_list(self, key: int) -> None:
        avail = self._available()
        if not avail:
            if key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_close()
            return

        if key == pygame.K_UP:
            old = self._list_sel
            self._list_sel = (self._list_sel - 1) % len(avail)
            if self._list_sel != old and self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_DOWN:
            old = self._list_sel
            self._list_sel = (self._list_sel + 1) % len(avail)
            if self._list_sel != old and self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._sfx_manager:
                self._sfx_manager.play("confirm")
            self._qty = 1
            self._state = "qty"
        elif key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._on_close()

    def _handle_qty(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = "list"
            return
        _, _, _, max_qty = sel

        if key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._state = "list"
        elif key == pygame.K_LEFT:
            self._qty_loop(-QTY_STEP_SMALL, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_RIGHT:
            self._qty_loop(QTY_STEP_SMALL, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_UP:
            self._qty_loop(-QTY_STEP_LARGE, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_DOWN:
            self._qty_loop(QTY_STEP_LARGE, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            _, _, rate, _ = sel
            if self._confirm_large and rate >= LARGE_RATE_THRESHOLD:
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._state = "confirm"
            else:
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._do_exchange()

    def _handle_confirm(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_y):
            if self._sfx_manager:
                self._sfx_manager.play("confirm")
            self._do_exchange()
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._state = "qty"

    # ── Exchange ──────────────────────────────────────────────

    def _do_exchange(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id, label, rate, max_qty = sel
        qty   = min(self._qty, max_qty)
        total = qty * rate

        repo = self._repo()
        entry = repo.get_item(item_id)
        if entry is None or entry.qty < qty:
            return

        repo.remove_item(item_id, qty)
        repo.add_gp(total)

        self._popup_text  = f"Exchanged {qty} x {label}    +{total:,} GP"
        self._state       = "popup"
        self._clamp_list_sel()

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen,
            state=self._state,
            avail=self._available(),
            list_sel=self._list_sel,
            qty=self._qty,
            popup_text=self._popup_text,
            gp=self._repo().gp,
            selected=self._selected(),
        )
