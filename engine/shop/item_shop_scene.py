# engine/shop/item_shop_scene.py

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.quantity_picker import QuantityPicker
from engine.common.scroll_list import ScrollListState
from engine.world.sprite_sheet import SpriteSheet
from engine.item.item_catalog import EQUIPMENT_TYPES, ItemCatalog, ItemDef
from engine.equipment.equipment_logic import can_equip, equip
from engine.shop.item_shop_renderer import (
    ItemShopRenderer, ShopViewState, SPRITE_SIZE, VISIBLE_ROWS,
)
from engine.shop.shop_constants import (
    MODE_BUY, MODE_SELL, STATE_EQUIP, STATE_LIST, STATE_POPUP, STATE_QTY,
)
from engine.shop.shop_scene_mixin import ShopSceneMixin

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 5


class ItemShopScene(ShopSceneMixin, Scene):
    """
    Item shop overlay. TAB toggles between buy and sell. States within
    each mode: list → qty → equip/toast (loop). ESC closes from list state,
    goes back from qty state, and skips the optional post-purchase equip prompt.
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
        title: str,
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
        self._state        = STATE_LIST   # list | qty | equip | popup
        self._list         = ScrollListState(VISIBLE_ROWS)
        self._picker       = QuantityPicker(QTY_STEP_SMALL, QTY_STEP_LARGE)
        self._popup_text   = ""
        self._equip_selection = 0
        self._pending_equip_item_id: str | None = None
        self._pending_buy_text = ""
        self._sell_tag: str | None = None  # None = show all sellable items
        self._sprite_surf: pygame.Surface | None = None
        self._sprite_loaded = False
        self._renderer = ItemShopRenderer(title=title)

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
        self._list.reset()
        self._play("hover")

    def _available(self) -> list[dict]:
        return self._buy_available() if self._mode == MODE_BUY else self._sell_available()

    def _selected(self) -> dict | None:
        return self._list.selected(self._available())

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

    def _item_def(self, item_id: str) -> ItemDef | None:
        return self._item_catalog.get(item_id)

    def _selected_item_def(self) -> ItemDef | None:
        sel = self._selected()
        if sel is None:
            return None
        return self._item_def(sel["id"])

    def _selected_is_equipment(self) -> bool:
        defn = self._selected_item_def()
        return defn is not None and defn.type in EQUIPMENT_TYPES

    def _pending_equip_def(self) -> ItemDef | None:
        if not self._pending_equip_item_id:
            return None
        return self._item_def(self._pending_equip_item_id)

    def _members(self):
        return list(self._holder.get().party.members)

    def _clamp_equip_selection(self) -> None:
        members = self._members()
        if not members:
            self._equip_selection = 0
            return
        self._equip_selection = max(0, min(self._equip_selection, len(members) - 1))

    def _has_equippable_member(self, item_def: ItemDef) -> bool:
        return any(can_equip(member, item_def) for member in self._members())

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == STATE_POPUP:
                self._handle_popup(event.key)
                return
            if self._state == STATE_EQUIP:
                self._handle_equip(event.key)
                return
            if self._state == STATE_LIST:
                self._handle_list(event.key)
            elif self._state == STATE_QTY:
                self._handle_qty(event.key)

    def _toggle_mode(self) -> None:
        self._mode = MODE_SELL if self._mode == MODE_BUY else MODE_BUY
        self._list.reset()
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
                self._close_shop()
            return

        if self._nav_list(key, len(avail)):
            return
        if key == pygame.K_LEFT and self._mode == MODE_BUY and self._selected_is_equipment():
            self._move_equip_selection(-1)
        elif key == pygame.K_RIGHT and self._mode == MODE_BUY and self._selected_is_equipment():
            self._move_equip_selection(1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self._selected()
            if sel is None:
                return
            if self._mode == MODE_BUY:
                if self._row_price(sel) <= self._holder.get().repository.gp:
                    self._play("confirm")
                    self._picker.reset()
                    self._state = STATE_QTY
            else:
                if sel["owned"] > 0:
                    self._play("confirm")
                    self._picker.reset()
                    self._state = STATE_QTY
        elif key == pygame.K_ESCAPE:
            self._close_shop()

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
            self._state = STATE_LIST
            return
        max_q = self._qty_max(sel)

        if key == pygame.K_ESCAPE:
            self._play("cancel")
            self._state = STATE_LIST
        elif key == pygame.K_LEFT:
            if self._picker.decrease_small(max_q):
                self._play("hover")
        elif key == pygame.K_RIGHT:
            if self._picker.increase_small(max_q):
                self._play("hover")
        elif key == pygame.K_UP:
            if self._picker.increase_large(max_q):
                self._play("hover")
        elif key == pygame.K_DOWN:
            if self._picker.decrease_large(max_q):
                self._play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._play("confirm")
            if self._mode == MODE_BUY:
                self._do_buy()
            else:
                self._do_sell()

    def _move_equip_selection(self, delta: int) -> None:
        members = self._members()
        if not members:
            return
        self._equip_selection = self._set_sel_hover(
            self._equip_selection,
            (self._equip_selection + delta) % len(members),
        )

    def _handle_equip(self, key: int) -> None:
        item_def = self._pending_equip_def()
        members = self._members()
        if item_def is None or not members:
            self._state = STATE_POPUP
            return

        self._clamp_equip_selection()
        if key == pygame.K_ESCAPE:
            self._play("cancel")
            self._popup_text = self._pending_buy_text
            self._pending_equip_item_id = None
            self._state = STATE_POPUP
        elif key == pygame.K_UP:
            self._move_equip_selection(-1)
        elif key == pygame.K_DOWN:
            self._move_equip_selection(1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            member = members[self._equip_selection]
            if not can_equip(member, item_def):
                self._play("cancel")
                return
            try:
                equip(member, self._holder.get().repository, self._item_catalog, item_def.id)
            except ValueError:
                self._play("cancel")
                return
            self._play("confirm")
            self._popup_text = f"Equipped {item_def.name} on {member.name}"
            self._pending_equip_item_id = None
            self._state = STATE_POPUP

    # ── Buy ───────────────────────────────────────────────────

    def _do_buy(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id = sel["id"]
        price   = self._row_price(sel)
        total   = price * self._picker.qty
        repo    = self._holder.get().repository

        if total > 0 and not repo.spend_gp(total):
            return  # not enough GP

        repo.add_item(item_id, self._picker.qty)
        # apply tags from shop data
        entry = repo.get_item(item_id)
        if entry:
            for tag in sel.get("tags", []):
                entry.tags.add(tag)

        name = self._display_name(sel)
        self._pending_buy_text = f"Bought {self._picker.qty} x {name}"
        item_def = self._item_def(item_id)
        if item_def is not None and item_def.type in EQUIPMENT_TYPES and self._has_equippable_member(item_def):
            self._pending_equip_item_id = item_id
            self._clamp_equip_selection()
            self._popup_text = f"Equip {name}?"
            self._state = STATE_EQUIP
        else:
            self._popup_text = self._pending_buy_text
            self._state = STATE_POPUP

    # ── Sell ──────────────────────────────────────────────────

    def _do_sell(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id = sel["id"]
        repo    = self._holder.get().repository
        gained  = repo.sell_item(item_id, self._picker.qty)
        name    = self._display_name(sel)
        if gained > 0:
            self._popup_text = f"Sold {self._picker.qty} x {name} for {gained:,} GP"
        else:
            self._popup_text = f"Cannot sell {name}"
        self._state = STATE_POPUP

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._sprite_loaded:
            self._init_sprite()

        self._renderer.render(screen, ShopViewState(
            mode=self._mode,
            sell_tag=self._sell_tag,
            state=self._state,
            avail=self._available(),
            list_sel=self._list.selection,
            scroll=self._list.scroll,
            qty=self._picker.qty,
            popup_text=self._popup_text,
            gp=self._holder.get().repository.gp,
            sprite_surf=self._sprite_surf,
            selected=self._selected(),
            owned_qty=self._owned_qty,
            display_name=self._display_name,
            row_price=self._row_price,
            description=self._description,
            members=self._members(),
            equip_selection=self._equip_selection,
            pending_equip_item_id=self._pending_equip_item_id,
            item_catalog=self._item_catalog,
        ))
