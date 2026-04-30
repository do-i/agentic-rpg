# engine/shop/apothecary_scene.py
#
# Apothecary overlay — crafting recipes from materials + magic cores + GP.

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
from engine.shop.apothecary_renderer import ApothecaryRenderer, SPRITE_SIZE, VISIBLE_ROWS

# MC size label → item id mapping
_MC_SIZE_TO_ID = {"XS": "mc_xs", "S": "mc_s", "M": "mc_m", "L": "mc_l", "XL": "mc_xl"}


class ApothecaryScene(MenuSfxMixin, Scene):
    """
    Apothecary overlay.  States: list → detail → toast (loop).
    ESC closes from list state, goes back from detail state.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        recipes: list[dict],
        sprite_path: Path,
        icon_paths: dict[str, Path] | None = None,
        *,
        sfx_manager,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close
        self._recipes       = recipes
        self._sprite_path   = sprite_path
        self._icon_paths    = icon_paths or {}
        self._sfx_manager   = sfx_manager

        self._state        = "list"   # list | detail | popup
        self._list_sel     = 0
        self._scroll       = 0
        self._popup_text   = ""
        self._sprite_surf: pygame.Surface | None = None
        self._sprite_loaded = False
        self._icons: dict[str, pygame.Surface] = {}
        self._icons_ready = False
        self._renderer = ApothecaryRenderer()

    # ── Init ──────────────────────────────────────────────────

    def _init_sprite(self) -> None:
        self._sprite_surf = SpriteSheet.load_npc_face(self._sprite_path, SPRITE_SIZE)
        self._sprite_loaded = True

    def _init_icons(self) -> None:
        target_h = 28
        for key, path in self._icon_paths.items():
            if not path.exists():
                continue
            raw = pygame.image.load(str(path)).convert_alpha()
            if raw.get_height() == 0:
                continue
            scale = target_h / raw.get_height()
            new_size = (max(1, int(raw.get_width() * scale)), target_h)
            self._icons[key] = pygame.transform.smoothscale(raw, new_size)
        self._icons_ready = True

    # ── Data ──────────────────────────────────────────────────

    def _visible_recipes(self) -> list[dict]:
        """All recipes — both locked and unlocked — shown in list."""
        return self._recipes

    def _is_unlocked(self, recipe: dict) -> bool:
        unlock = recipe.get("unlock_flag")
        if not unlock:
            return True
        return self._holder.get().flags.has_flag(unlock)

    def _has_inputs(self, recipe: dict) -> bool:
        """Check if player has all required inputs."""
        repo = self._holder.get().repository
        inputs = recipe.get("inputs", {})
        # check items
        for req in inputs.get("items", []):
            if not repo.has_item(req["id"], req["qty"]):
                return False
        # check magic cores
        for req in inputs.get("mc", []):
            mc_id = _MC_SIZE_TO_ID.get(req["size"])
            if not mc_id or not repo.has_item(mc_id, req["qty"]):
                return False
        return True

    def _can_afford(self, recipe: dict) -> bool:
        return self._holder.get().repository.gp >= recipe["gp_cost"]

    def _is_duplicate_blocked(self, recipe: dict) -> bool:
        """Unique-output recipes (e.g. key items like veil_breaker) are blocked
        once the player already owns the output — prevents crafting duplicates
        while still letting the recipe stay visible in the list."""
        if not recipe.get("unique_output"):
            return False
        out_id = recipe.get("output", {}).get("item")
        if not out_id:
            return False
        return self._owned_qty(out_id) >= 1

    def _can_craft(self, recipe: dict) -> bool:
        if self._is_duplicate_blocked(recipe):
            return False
        return self._is_unlocked(recipe) and self._has_inputs(recipe) and self._can_afford(recipe)

    def _selected(self) -> dict | None:
        recipes = self._visible_recipes()
        if not recipes:
            return None
        idx = min(self._list_sel, len(recipes) - 1)
        return recipes[idx]

    def _owned_qty(self, item_id: str) -> int:
        entry = self._holder.get().repository.get_item(item_id)
        return entry.qty if entry else 0

    def _item_name(self, item_id: str) -> str:
        entry = self._holder.get().repository.get_item(item_id)
        if entry and entry.name:
            return entry.name
        return item_id.replace("_", " ").title()

    def _mc_name(self, size: str) -> str:
        return f"Magic Core ({size})"

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
            elif self._state == "detail":
                self._handle_detail(event.key)

    def _handle_list(self, key: int) -> None:
        recipes = self._visible_recipes()
        if not recipes:
            if key == pygame.K_ESCAPE:
                self._play("cancel")
                self._on_close()
            return

        if key == pygame.K_UP:
            self._list_sel = self._set_sel_hover(self._list_sel, max(0, self._list_sel - 1))
            self._clamp_scroll()
        elif key == pygame.K_DOWN:
            self._list_sel = self._set_sel_hover(self._list_sel, min(len(recipes) - 1, self._list_sel + 1))
            self._clamp_scroll()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self._selected()
            if sel and self._is_unlocked(sel) and not self._is_duplicate_blocked(sel):
                self._play("confirm")
                self._state = "detail"
            else:
                self._play("cancel")
        elif key == pygame.K_ESCAPE:
            self._play("cancel")
            self._on_close()

    def _handle_detail(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = "list"
            return
        if key == pygame.K_ESCAPE:
            self._play("cancel")
            self._state = "list"
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._can_craft(sel):
                self._play("confirm")
                self._do_craft(sel)

    def _clamp_scroll(self) -> None:
        self._scroll = ItemSelectionView.clamp_scroll(
            self._list_sel, self._scroll, len(self._visible_recipes()), VISIBLE_ROWS,
        )

    # ── Craft ─────────────────────────────────────────────────

    def _do_craft(self, recipe: dict) -> None:
        repo = self._holder.get().repository
        gp_cost = recipe["gp_cost"]
        inputs = recipe.get("inputs", {})

        # consume GP
        if gp_cost > 0 and not repo.spend_gp(gp_cost):
            return

        # consume items
        for req in inputs.get("items", []):
            repo.remove_item(req["id"], req["qty"])

        # consume magic cores
        for req in inputs.get("mc", []):
            mc_id = _MC_SIZE_TO_ID.get(req["size"])
            if mc_id:
                repo.remove_item(mc_id, req["qty"])

        # produce output
        output = recipe.get("output", {})
        out_id = output.get("item")
        out_qty = output.get("qty", 1)
        if out_id:
            repo.add_item(out_id, out_qty)

        out_name = self._item_name(out_id) if out_id else "???"
        self._popup_text  = f"Crafted {out_qty} x {out_name}"
        self._state       = "popup"

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._sprite_loaded:
            self._init_sprite()
        if not self._icons_ready:
            self._init_icons()

        self._renderer.render(
            screen,
            state=self._state,
            recipes=self._visible_recipes(),
            list_sel=self._list_sel,
            scroll=self._scroll,
            popup_text=self._popup_text,
            gp=self._holder.get().repository.gp,
            sprite_surf=self._sprite_surf,
            icons=self._icons,
            is_unlocked=self._is_unlocked,
            has_inputs=self._has_inputs,
            can_afford=self._can_afford,
            can_craft=self._can_craft,
            item_name=self._item_name,
            mc_name=self._mc_name,
            owned_qty=self._owned_qty,
            selected=self._selected(),
            is_duplicate_blocked=self._is_duplicate_blocked,
        )
