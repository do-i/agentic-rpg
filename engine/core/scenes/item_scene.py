# engine/core/scenes/item_scene.py
#
# Phase 6 — Shop + Apothecary
# Thin orchestrator: delegates logic to item_logic, rendering to item_renderer.

from __future__ import annotations

import pygame
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.repository_state import ItemEntry, RepositoryState
from engine.core.item.item_effect_handler import ItemEffectHandler
from engine.core.scenes.target_select_overlay import TargetSelectOverlay
from engine.core.scenes.item_logic import (
    TABS, filtered_items, actions_for, is_usable, discard_item, clamp_scroll,
    display_name,
)
from engine.core.scenes.item_renderer import ItemRenderer, VISIBLE_ROWS


# ── Debug stub data ───────────────────────────────────────────
def _make_debug_repository() -> RepositoryState:
    r = RepositoryState(gp=3200)
    items = [
        ("potion",       5,  {"consumable", "recovery"},  "Restores 100 HP to one ally.",                   False),
        ("hi_potion",    3,  {"consumable", "recovery"},  "Restores 500 HP to one ally.",                   False),
        ("elixir",       1,  {"consumable", "recovery"},  "Fully restores HP and MP of one ally.",          True),
        ("ether",        2,  {"consumable", "recovery"},  "Restores 50 MP to one ally.",                    False),
        ("antidote",     4,  {"consumable", "status"},    "Cures poison from one ally.",                    False),
        ("echo_herb",    2,  {"consumable", "status"},    "Cures silence from one ally.",                   False),
        ("remedy",       1,  {"consumable", "status"},    "Cures poison, silence, and sleep.",              False),
        ("fire_vial",    3,  {"battle"},                  "Deals 150 fire damage to one enemy.",            False),
        ("holy_water",   2,  {"battle"},                  "Deals 200 holy damage. Bonus vs undead/demon.",  False),
        ("tent",         2,  {"consumable", "recovery"},  "Restores HP and MP of all allies on world map.", False),
        ("wolf_fang",    6,  {"material"},                "A sharp fang. Used in crafting.",                False),
        ("spider_silk",  4,  {"material"},                "Fine silk thread. Used in crafting.",            False),
        ("venom_sac",    3,  {"material"},                "A sac filled with venom. Used in crafting.",     False),
        ("rare_herb",    2,  {"material"},                "A rare medicinal herb. Used in crafting.",       False),
        ("mc_xl",        1,  {"magic_core"},              "A huge Magic Core. High crafting value.",        False),
        ("mc_l",         3,  {"magic_core"},              "A large Magic Core.",                            False),
        ("mc_m",         8,  {"magic_core"},              "A medium Magic Core.",                           False),
        ("mc_s",        15,  {"magic_core"},              "A small Magic Core.",                            False),
        ("mc_xs",       42,  {"magic_core"},              "A tiny Magic Core. Exchange for GP in bulk.",    False),
        ("phoenix_wing", 1,  {"key"},                     "Revives a fallen ally on the world map. Never consumed.", True),
        ("veil_breaker", 1,  {"consumable", "battle"},    "Allows attacks to reach barrier-type enemies.",  False),
    ]
    for item_id, qty, tags, desc, locked in items:
        r.add_item(item_id, qty)
        entry = r.get_item(item_id)
        entry.tags = tags
        entry.locked = locked
        entry.description = desc  # type: ignore[attr-defined]
    return r


class ItemScene(Scene):
    """
    Party repository item screen.
    I / ESC to close. Tab left/right with Q/E. Up/Down navigate list.
    Use action opens TargetSelectOverlay (single target) or AOE confirm.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        debug_items: bool,
        effect_handler: ItemEffectHandler,
        use_aoe_confirm: bool = True,
        return_scene_name: str = "world_map",
    ) -> None:
        self._holder       = holder
        self._scene_manager = scene_manager
        self._registry     = registry
        self._return_scene_name = return_scene_name
        self._effect_handler = effect_handler
        self._use_aoe_confirm = use_aoe_confirm

        self._tab_index:   int  = 0
        self._list_sel:    int  = 0
        self._scroll:      int  = 0
        self._action_sel:  int  = 0
        self._in_tab:      bool = True
        self._in_action:   bool = False
        self._confirm_discard: bool = False

        # overlays
        self._target_overlay: TargetSelectOverlay | None = None
        self._aoe_confirm:    bool = False

        self._renderer = ItemRenderer(effect_handler)
        self._debug_repo  = _make_debug_repository()
        self._debug_items = debug_items

    # ── Data helpers ──────────────────────────────────────────

    def _get_repo(self) -> RepositoryState:
        if self._debug_items:
            return self._debug_repo
        try:
            return self._holder.get().repository
        except RuntimeError:
            return self._debug_repo

    def _get_party(self):
        try:
            return self._holder.get().party
        except RuntimeError:
            return None

    def _filtered_items(self) -> list[ItemEntry]:
        return filtered_items(self._get_repo(), self._tab_index)

    def _selected_entry(self) -> ItemEntry | None:
        items = self._filtered_items()
        if not items:
            return None
        return items[min(self._list_sel, len(items) - 1)]

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if self._confirm_discard:
                self._handle_confirm_discard(event.key)
                return
            if self._aoe_confirm:
                self._handle_aoe_confirm(event.key)
                return

            if event.key == pygame.K_i:
                self._close()
            elif self._in_tab:
                self._handle_tab_key(event.key)
            elif not self._in_action:
                self._handle_list_key(event.key)
            else:
                self._handle_action_key(event.key)

    def _close(self) -> None:
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    def _handle_tab_key(self, key: int) -> None:
        if key == pygame.K_LEFT:
            self._tab_index = (self._tab_index - 1) % len(TABS)
            self._list_sel = 0
            self._scroll = 0
        elif key == pygame.K_RIGHT:
            self._tab_index = (self._tab_index + 1) % len(TABS)
            self._list_sel = 0
            self._scroll = 0
        elif key == pygame.K_ESCAPE:
            self._close()
        elif key == pygame.K_RETURN:
            if self._filtered_items():
                self._in_tab = False

    def _handle_list_key(self, key: int) -> None:
        items = self._filtered_items()
        if not items:
            return
        if key == pygame.K_UP:
            self._list_sel = max(0, self._list_sel - 1)
            self._scroll = clamp_scroll(self._list_sel, self._scroll, VISIBLE_ROWS)
        elif key == pygame.K_DOWN:
            self._list_sel = min(len(items) - 1, self._list_sel + 1)
            self._scroll = clamp_scroll(self._list_sel, self._scroll, VISIBLE_ROWS)
        elif key == pygame.K_RETURN:
            self._in_action = True
            self._action_sel = 0
        elif key == pygame.K_ESCAPE:
            self._in_tab = True
            self._in_action = False
            self._confirm_discard = False
            self._aoe_confirm = False

    def _handle_action_key(self, key: int) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        item_actions = actions_for(entry, self._effect_handler)
        if key in (pygame.K_LEFT, pygame.K_ESCAPE):
            self._in_action = False
        elif key == pygame.K_UP:
            self._action_sel = max(0, self._action_sel - 1)
        elif key == pygame.K_DOWN:
            self._action_sel = min(len(item_actions) - 1, self._action_sel + 1)
        elif key == pygame.K_RETURN:
            label = item_actions[self._action_sel]
            if label == "Use":
                self._begin_use(entry)
            elif label == "Discard" and not entry.locked:
                self._confirm_discard = True

    def _handle_confirm_discard(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_y):
            entry = self._selected_entry()
            if entry:
                discard_item(self._get_repo(), entry)
                items = self._filtered_items()
                self._list_sel = min(self._list_sel, max(0, len(items) - 1))
            self._confirm_discard = False
            self._in_action = False
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            self._confirm_discard = False

    def _handle_aoe_confirm(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_y):
            self._apply_aoe()
            self._aoe_confirm = False
            self._in_action = False
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            self._aoe_confirm = False

    # ── Use flow ──────────────────────────────────────────────

    def _begin_use(self, entry: ItemEntry) -> None:
        defn = self._effect_handler.get_def(entry.id)
        if not defn:
            return
        party = self._get_party()
        if not party:
            return

        if defn.target == "all_alive":
            if self._use_aoe_confirm:
                self._aoe_confirm = True
            else:
                self._apply_aoe()
                self._in_action = False
        else:
            targets = self._effect_handler.valid_targets(entry.id, party)
            label = entry.id.replace("_", " ").title()
            self._target_overlay = TargetSelectOverlay(
                targets=targets,
                item_label=label,
                on_confirm=self._on_target_confirm,
                on_cancel=self._on_target_cancel,
            )

    def _on_target_confirm(self, member) -> None:
        entry = self._selected_entry()
        if not entry:
            self._target_overlay = None
            return
        repo   = self._get_repo()
        result = self._effect_handler.apply(entry.id, [member], repo)
        if result.warning:
            self._target_overlay.warning = result.warning
        else:
            self._target_overlay = None
            self._in_action = False
            items = self._filtered_items()
            self._list_sel = min(self._list_sel, max(0, len(items) - 1))

    def _on_target_cancel(self) -> None:
        self._target_overlay = None

    def _apply_aoe(self) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        party = self._get_party()
        if not party:
            return
        targets = self._effect_handler.valid_targets(entry.id, party)
        repo    = self._get_repo()
        self._effect_handler.apply(entry.id, targets, repo)
        items = self._filtered_items()
        self._list_sel = min(self._list_sel, max(0, len(items) - 1))

    # ── Render (delegates to ItemRenderer) ────────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen,
            gp=self._get_repo().gp,
            tab_index=self._tab_index,
            items=self._filtered_items(),
            list_sel=self._list_sel,
            scroll=self._scroll,
            in_tab=self._in_tab,
            in_action=self._in_action,
            action_sel=self._action_sel,
            selected_entry=self._selected_entry(),
            confirm_discard=self._confirm_discard,
            aoe_confirm=self._aoe_confirm,
            target_overlay=self._target_overlay,
        )
