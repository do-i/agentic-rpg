# engine/shop/item_shop_scene.py

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.world.sprite_sheet import SpriteSheet
from engine.common.item_selection_view import ItemSelectionView
from engine.shop.item_shop_renderer import ItemShopRenderer, SPRITE_SIZE, VISIBLE_ROWS

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 5


class ItemShopScene(Scene):
    """
    Item shop overlay.  States: list → qty → toast (loop).
    ESC closes from list state, goes back from qty state.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        shop_items: list[dict],
        sprite_path: Path,
        sfx_manager=None,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close
        self._shop_items    = shop_items
        self._sprite_path   = sprite_path
        self._sfx_manager   = sfx_manager

        self._state        = "list"   # list | qty | popup
        self._list_sel     = 0
        self._scroll       = 0
        self._qty          = 1
        self._popup_text   = ""
        self._sprite_surf: pygame.Surface | None = None
        self._sprite_loaded = False
        self._renderer = ItemShopRenderer()

    # ── Init ──────────────────────────────────────────────────

    def _init_sprite(self) -> None:
        self._sprite_surf = SpriteSheet.load_npc_face(self._sprite_path, SPRITE_SIZE)
        self._sprite_loaded = True

    # ── Data ──────────────────────────────────────────────────

    def _available(self) -> list[dict]:
        """Shop items unlocked by current flags."""
        flags = self._holder.get().flags
        result = []
        for item in self._shop_items:
            unlock = item.get("unlock_flag")
            if unlock and not flags.has_flag(unlock):
                continue
            result.append(item)
        return result

    def _selected(self) -> dict | None:
        avail = self._available()
        if not avail:
            return None
        idx = min(self._list_sel, len(avail) - 1)
        return avail[idx]

    def _owned_qty(self, item_id: str) -> int:
        entry = self._holder.get().repository.get_item(item_id)
        return entry.qty if entry else 0

    def _display_name(self, item: dict) -> str:
        return item.get("name", item["id"].replace("_", " ").title())

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "popup":
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._state = "list"
                return
            if self._state == "list":
                self._handle_list(event.key)
            elif self._state == "qty":
                self._handle_qty(event.key)

    def _handle_list(self, key: int) -> None:
        avail = self._available()
        if not avail:
            if key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_close()
            return

        if key == pygame.K_UP:
            new = max(0, self._list_sel - 1)
            if new != self._list_sel and self._sfx_manager:
                self._sfx_manager.play("hover")
            self._list_sel = new
            self._clamp_scroll()
        elif key == pygame.K_DOWN:
            new = min(len(avail) - 1, self._list_sel + 1)
            if new != self._list_sel and self._sfx_manager:
                self._sfx_manager.play("hover")
            self._list_sel = new
            self._clamp_scroll()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self._selected()
            if sel and sel["buy_price"] <= self._holder.get().repository.gp:
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._qty   = 1
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
        price  = sel["buy_price"]
        owned  = self._owned_qty(sel["id"])
        repo   = self._holder.get().repository
        max_q  = repo.item_qty_cap - owned
        gp     = repo.gp
        if price > 0:
            max_q = min(max_q, gp // price)
        max_q = max(max_q, 1)

        if key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._state = "list"
        elif key == pygame.K_LEFT:
            self._qty = max(1, self._qty - QTY_STEP_SMALL)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_RIGHT:
            self._qty = min(max_q, self._qty + QTY_STEP_SMALL)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_UP:
            self._qty = min(max_q, self._qty + QTY_STEP_LARGE)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_DOWN:
            self._qty = max(1, self._qty - QTY_STEP_LARGE)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._sfx_manager:
                self._sfx_manager.play("confirm")
            self._do_buy()

    def _clamp_scroll(self) -> None:
        self._scroll = ItemSelectionView.clamp_scroll(
            self._list_sel, self._scroll, len(self._available()), VISIBLE_ROWS,
        )

    # ── Buy ───────────────────────────────────────────────────

    def _do_buy(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id = sel["id"]
        price   = sel["buy_price"]
        total   = price * self._qty
        repo    = self._holder.get().repository

        if total > 0 and not repo.spend_gp(total):
            return  # not enough GP

        repo.add_item(item_id, self._qty)
        # apply tags from shop data
        entry = repo.get_item(item_id)
        if entry:
            for tag in sel.get("tags", []):
                entry.tags.add(tag)

        name = self._display_name(sel)
        self._popup_text  = f"Bought {self._qty} x {name}"
        self._state       = "popup"

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._sprite_loaded:
            self._init_sprite()

        self._renderer.render(
            screen,
            state=self._state,
            avail=self._available(),
            list_sel=self._list_sel,
            scroll=self._scroll,
            qty=self._qty,
            popup_text=self._popup_text,
            gp=self._holder.get().repository.gp,
            sprite_surf=self._sprite_surf,
            selected=self._selected(),
            owned_qty=self._owned_qty,
            display_name=self._display_name,
        )
