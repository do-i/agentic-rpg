# engine/shop/item_shop_scene.py

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.menu_sfx_mixin import MenuSfxMixin
from engine.world.sprite_sheet import SpriteSheet
from engine.common.item_selection_view import ItemSelectionView
from engine.item.item_catalog import ItemCatalog
from engine.shop.item_shop_renderer import ItemShopRenderer, SPRITE_SIZE, VISIBLE_ROWS

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 5

MODE_BUY = "buy"
MODE_SELL = "sell"


class ItemShopScene(MenuSfxMixin, Scene):
    """
    Item shop overlay. TAB toggles between buy and sell. States within
    each mode: list → qty → toast (loop). ESC closes from list state,
    goes back from qty state.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        shop_items: list[dict],
        sprite_path: Path,
        sfx_manager,
        item_catalog: ItemCatalog,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close
        self._shop_items    = shop_items
        self._sprite_path   = sprite_path
        self._sfx_manager   = sfx_manager
        self._item_catalog  = item_catalog

        self._mode         = MODE_BUY
        self._state        = "list"   # list | qty | popup
        self._list_sel     = 0
        self._scroll       = 0
        self._qty          = 1
        self._popup_text   = ""
        self._sell_tag: str | None = None  # None = show all sellable items
        self._sprite_surf: pygame.Surface | None = None
        self._sprite_loaded = False
        self._renderer = ItemShopRenderer()

    # ── Init ──────────────────────────────────────────────────

    def _init_sprite(self) -> None:
        self._sprite_surf = SpriteSheet.load_npc_face(self._sprite_path, SPRITE_SIZE)
        self._sprite_loaded = True

    # ── Data ──────────────────────────────────────────────────

    def _buy_available(self) -> list[dict]:
        """Shop items unlocked by current flags."""
        flags = self._holder.get().flags
        result = []
        for item in self._shop_items:
            unlock = item.get("unlock_flag")
            if unlock and not flags.has_flag(unlock):
                continue
            result.append(item)
        return result

    def _sell_available(self) -> list[dict]:
        """Repository items the player can sell: sellable, non-locked, qty > 0.

        Returns dict rows shaped like buy items so the renderer can stay
        mode-agnostic: id, name, price, owned (qty in repo).
        """
        repo = self._holder.get().repository
        result: list[dict] = []
        for entry in repo.items:
            if entry.locked or not entry.sellable or entry.qty <= 0:
                continue
            if self._sell_tag is not None and self._sell_tag not in entry.tags:
                continue
            result.append({
                "id":    entry.id,
                "name":  entry.name,
                "price": entry.sell_price,
                "owned": entry.qty,
            })
        return result

    def _sell_tags(self) -> list[str]:
        """Unique tags across all sellable repository entries (sorted)."""
        repo = self._holder.get().repository
        tags: set[str] = set()
        for entry in repo.items:
            if entry.locked or not entry.sellable or entry.qty <= 0:
                continue
            tags.update(entry.tags)
        return sorted(tags)

    def _cycle_sell_tag(self) -> None:
        """Cycle filter through: None (All) → tag1 → tag2 → ... → None."""
        tags = self._sell_tags()
        if not tags:
            return
        order: list[str | None] = [None] + tags
        try:
            i = order.index(self._sell_tag)
        except ValueError:
            i = 0
        self._sell_tag = order[(i + 1) % len(order)]
        self._list_sel = 0
        self._scroll = 0
        self._play("hover")

    def _available(self) -> list[dict]:
        return self._buy_available() if self._mode == MODE_BUY else self._sell_available()

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

    def _description(self, item: dict) -> str:
        item_def = self._item_catalog.get(item["id"])
        return item_def.description if item_def else ""

    def _row_price(self, item: dict) -> int:
        # buy rows use "buy_price"; sell rows already normalize to "price".
        return item.get("price", item.get("buy_price", 0))

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "popup":
                if self.is_popup_dismiss_key(event.key):
                    self._state = "list"
                return
            if self._state == "list":
                self._handle_list(event.key)
            elif self._state == "qty":
                self._handle_qty(event.key)

    def _toggle_mode(self) -> None:
        self._mode = MODE_SELL if self._mode == MODE_BUY else MODE_BUY
        self._list_sel = 0
        self._scroll = 0
        self._sell_tag = None
        self._play("hover")

    def _handle_list(self, key: int) -> None:
        avail = self._available()

        if key == pygame.K_TAB:
            self._toggle_mode()
            return

        if key == pygame.K_t and self._mode == MODE_SELL:
            self._cycle_sell_tag()
            return

        if not avail:
            if key == pygame.K_ESCAPE:
                self._play("cancel")
                self._on_close()
            return

        if key == pygame.K_UP:
            self._list_sel = self._set_sel_hover(self._list_sel, max(0, self._list_sel - 1))
            self._clamp_scroll()
        elif key == pygame.K_DOWN:
            self._list_sel = self._set_sel_hover(self._list_sel, min(len(avail) - 1, self._list_sel + 1))
            self._clamp_scroll()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self._selected()
            if sel is None:
                return
            if self._mode == MODE_BUY:
                if self._row_price(sel) <= self._holder.get().repository.gp:
                    self._play("confirm")
                    self._qty   = 1
                    self._state = "qty"
            else:
                if sel["owned"] > 0:
                    self._play("confirm")
                    self._qty   = 1
                    self._state = "qty"
        elif key == pygame.K_ESCAPE:
            self._play("cancel")
            self._on_close()

    def _qty_max(self, sel: dict) -> int:
        repo = self._holder.get().repository
        if self._mode == MODE_BUY:
            owned = self._owned_qty(sel["id"])
            price = self._row_price(sel)
            cap = repo.item_qty_cap - owned
            if price > 0:
                cap = min(cap, repo.gp // price)
            return max(cap, 1)
        # sell: cap is owned qty
        return max(sel["owned"], 1)

    def _handle_qty(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = "list"
            return
        max_q = self._qty_max(sel)

        if key == pygame.K_ESCAPE:
            self._play("cancel")
            self._state = "list"
        elif key == pygame.K_LEFT:
            self._qty = self._set_sel_hover(self._qty, max(1, self._qty - QTY_STEP_SMALL))
        elif key == pygame.K_RIGHT:
            self._qty = self._set_sel_hover(self._qty, min(max_q, self._qty + QTY_STEP_SMALL))
        elif key == pygame.K_UP:
            self._qty = self._set_sel_hover(self._qty, min(max_q, self._qty + QTY_STEP_LARGE))
        elif key == pygame.K_DOWN:
            self._qty = self._set_sel_hover(self._qty, max(1, self._qty - QTY_STEP_LARGE))
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._play("confirm")
            if self._mode == MODE_BUY:
                self._do_buy()
            else:
                self._do_sell()

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
        price   = self._row_price(sel)
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

    # ── Sell ──────────────────────────────────────────────────

    def _do_sell(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id = sel["id"]
        repo    = self._holder.get().repository
        gained  = repo.sell_item(item_id, self._qty)
        name    = self._display_name(sel)
        if gained > 0:
            self._popup_text = f"Sold {self._qty} x {name} for {gained:,} GP"
        else:
            self._popup_text = f"Cannot sell {name}"
        self._state = "popup"

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._sprite_loaded:
            self._init_sprite()

        self._renderer.render(
            screen,
            mode=self._mode,
            sell_tag=self._sell_tag,
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
            row_price=self._row_price,
            description=self._description,
        )
