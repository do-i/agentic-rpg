# engine/item/item_scene.py
#
# Party repository item screen — three-column wizard (Pouch -> List) with the
# heavier concerns (use targeting, discard, tag editing, show/hide) lifted into
# modal overlays. Built on engine.common.wizard_scene so navigation, hover SFX
# and the scene-close path are shared with Equip/Spell.
#
#   POUCH page : category column is live; UP/DOWN pick a pouch, ENTER opens it.
#   LIST  page : item list is live with a live detail peek on the right.
#                ENTER opens the action modal; M opens the manage (show/hide)
#                modal; ESC backs out to the pouch column.
#   I          : close the scene from anywhere.

from __future__ import annotations

import pygame

from engine.common.wizard_scene import WizardPage, WizardScene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.item.item_entry_state import ItemEntry
from engine.party.repository_state import RepositoryState
from engine.item.item_effect_handler import ItemEffectHandler
from engine.common.target_select_overlay_renderer import TargetSelectOverlay
from engine.item.item_logic import (
    TABS, filtered_items, actions_for,
    discard_item,
    EDITABLE_SYSTEM_TAGS, custom_tags, normalize_custom_tag,
    CUSTOM_TAG_MAX_LEN,
)
from engine.item.magic_core_catalog_state import MagicCoreCatalogState
from engine.item.item_renderer import ItemRenderer

PAGE_POUCH = "pouch"
PAGE_LIST  = "list"

# Modal overlay ids (mutually exclusive; target overlay is tracked separately).
M_ACTION  = "action"
M_DISCARD = "discard"
M_AOE     = "aoe"
M_TAGS    = "tags"
M_NEWTAG  = "newtag"
M_MANAGE  = "manage"


class ItemScene(WizardScene):
    """Pouch -> List wizard with action / discard / tags / manage modals."""

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        effect_handler: ItemEffectHandler,
        mc_catalog: MagicCoreCatalogState | None = None,
        use_aoe_confirm: bool = True,
        return_scene_name: str = "world_map",
        *,
        sfx_manager,
    ) -> None:
        super().__init__(scene_manager, registry, return_scene_name, sfx_manager)
        self._holder = holder
        self._effect_handler = effect_handler
        self._mc_catalog = mc_catalog
        self._use_aoe_confirm = use_aoe_confirm

        # Modal state.
        self._modal: str | None = None
        self._target_overlay: TargetSelectOverlay | None = None
        self._action_sel: int = 0
        self._discard_qty: int = 1
        self._manage_sel: int = 0
        self._tag_editor_sel: int = 0
        self._tag_input: str = ""
        self._tag_warning: str = ""
        self._tag_warning_t: int = 0

        self._renderer = ItemRenderer(effect_handler, mc_catalog)

        self._register_page(WizardPage(
            name=PAGE_POUCH,
            count_fn=lambda: len(TABS),
            on_confirm=self._confirm_pouch,
            on_back=lambda: None,            # close scene
        ))
        self._register_page(WizardPage(
            name=PAGE_LIST,
            count_fn=lambda: len(self._filtered_items()),
            on_confirm=self._confirm_list,
            on_back=lambda: PAGE_POUCH,
        ))

    # ── Data helpers ──────────────────────────────────────────

    def _get_repo(self) -> RepositoryState:
        return self._holder.get().repository

    def _get_party(self):
        try:
            return self._holder.get().party
        except RuntimeError:
            return None

    @property
    def _tab_index(self) -> int:
        return self._page(PAGE_POUCH).selection

    @property
    def _list_sel(self) -> int:
        return self._page(PAGE_LIST).selection

    def _filtered_items(self) -> list[ItemEntry]:
        return filtered_items(self._get_repo(), self._tab_index, self._mc_catalog)

    def _manage_entries(self) -> list[ItemEntry]:
        """All owned items (including hidden) for the manage modal."""
        return sorted(self._get_repo().items, key=lambda e: e.id)

    def _selected_entry(self) -> ItemEntry | None:
        items = self._filtered_items()
        if not items:
            return None
        return items[min(self._list_sel, len(items) - 1)]

    def _clamp_list_sel(self) -> None:
        page = self._page(PAGE_LIST)
        items = self._filtered_items()
        page.selection = min(page.selection, max(0, len(items) - 1))

    # ── Page callbacks ────────────────────────────────────────

    def _confirm_pouch(self) -> str | None:
        # Always enter the list page; an empty pouch still lets the player open
        # the manage modal (M) to unhide items.
        self._play("confirm")
        return PAGE_LIST

    def _confirm_list(self) -> str | None:
        if self._selected_entry() is not None:
            self._open_action()
        return None  # stay on the list page; the modal takes over

    # ── Top-level input ───────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._is_input_blocked():
            self._handle_blocked_input(events)
            return

        rest: list[pygame.event.Event] = []
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    self._close_scene()
                    return
                if self.page_id == PAGE_LIST and event.key == pygame.K_m:
                    self._open_manage()
                    continue
            rest.append(event)
        super().handle_events(rest)

    # ── Modal plumbing ────────────────────────────────────────

    def _is_input_blocked(self) -> bool:
        return self._modal is not None or self._target_overlay is not None

    def _handle_blocked_input(self, events: list[pygame.event.Event]) -> None:
        if self._target_overlay:
            self._target_overlay.handle_events(events)
            return
        if self._modal == M_NEWTAG:
            for event in events:
                self._handle_new_tag_event(event)
            return
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._modal == M_ACTION:
                self._handle_action_key(event.key)
            elif self._modal == M_DISCARD:
                self._handle_discard_key(event.key)
            elif self._modal == M_AOE:
                self._handle_aoe_key(event.key)
            elif self._modal == M_TAGS:
                self._handle_tags_key(event.key)
            elif self._modal == M_MANAGE:
                self._handle_manage_key(event.key)

    # ── Action modal ──────────────────────────────────────────

    def _action_options(self, entry: ItemEntry) -> list[str]:
        opts = [a for a in actions_for(entry, self._effect_handler) if a != "-"]
        opts.append("Edit Tags")
        return opts

    def _open_action(self) -> None:
        self._modal = M_ACTION
        self._action_sel = 0
        self._play("confirm")

    def _handle_action_key(self, key: int) -> None:
        entry = self._selected_entry()
        if not entry:
            self._modal = None
            return
        opts = self._action_options(entry)
        if key in (pygame.K_LEFT, pygame.K_ESCAPE):
            self._play("cancel")
            self._modal = None
        elif key == pygame.K_UP:
            self._action_sel = max(0, self._action_sel - 1)
            self._play("hover")
        elif key == pygame.K_DOWN:
            self._action_sel = min(len(opts) - 1, self._action_sel + 1)
            self._play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            label = opts[self._action_sel]
            if label == "Use":
                self._play("confirm")
                self._begin_use(entry)
            elif label == "Discard":
                self._play("confirm")
                self._modal = M_DISCARD
                self._discard_qty = 1
            elif label == "Edit Tags":
                self._play("confirm")
                self._open_tags()

    # ── Use flow ──────────────────────────────────────────────

    def _begin_use(self, entry: ItemEntry) -> None:
        defn = self._effect_handler.get_def(entry.id)
        party = self._get_party()
        if not defn or not party:
            return
        if defn.target == "all_alive":
            if self._use_aoe_confirm:
                self._modal = M_AOE
            else:
                self._apply_aoe()
                self._modal = None
        else:
            targets = self._effect_handler.valid_targets(entry.id, party)
            label = entry.id.replace("_", " ").title()
            self._target_overlay = TargetSelectOverlay(
                targets=targets,
                item_label=label,
                on_confirm=self._on_target_confirm,
                on_cancel=self._on_target_cancel,
                sfx_manager=self._sfx_manager,
            )

    def _on_target_confirm(self, member) -> None:
        entry = self._selected_entry()
        if not entry:
            self._target_overlay = None
            self._modal = None
            return
        result = self._effect_handler.apply(entry.id, [member], self._get_repo())
        if result.warning:
            self._target_overlay.warning = result.warning
        else:
            self._target_overlay = None
            self._modal = None
            self._clamp_list_sel()

    def _on_target_cancel(self) -> None:
        self._target_overlay = None
        # Drop back to the action modal so the player can pick again.

    def _apply_aoe(self) -> None:
        entry = self._selected_entry()
        party = self._get_party()
        if not entry or not party:
            return
        targets = self._effect_handler.valid_targets(entry.id, party)
        self._effect_handler.apply(entry.id, targets, self._get_repo())
        self._clamp_list_sel()

    def _handle_aoe_key(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
            self._play("confirm")
            self._apply_aoe()
            self._modal = None
        elif key in (pygame.K_ESCAPE, pygame.K_n, pygame.K_LEFT):
            self._play("cancel")
            self._modal = M_ACTION

    # ── Discard modal ─────────────────────────────────────────

    def _handle_discard_key(self, key: int) -> None:
        entry = self._selected_entry()
        if not entry:
            self._modal = None
            return
        if key in (pygame.K_LEFT, pygame.K_DOWN):
            new = max(1, self._discard_qty - 1)
            if new != self._discard_qty:
                self._play("hover")
            self._discard_qty = new
        elif key in (pygame.K_RIGHT, pygame.K_UP):
            new = min(entry.qty, self._discard_qty + 1)
            if new != self._discard_qty:
                self._play("hover")
            self._discard_qty = new
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
            self._play("confirm")
            discard_item(self._get_repo(), entry, self._discard_qty)
            self._clamp_list_sel()
            self._modal = None
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            self._play("cancel")
            self._modal = M_ACTION

    # ── Manage (show/hide) modal ──────────────────────────────

    def _open_manage(self) -> None:
        entries = self._manage_entries()
        if not entries:
            self._play("cancel")
            return
        self._play("confirm")
        self._modal = M_MANAGE
        self._manage_sel = min(self._manage_sel, len(entries) - 1)

    def _handle_manage_key(self, key: int) -> None:
        entries = self._manage_entries()
        if not entries:
            self._modal = None
            return
        if key == pygame.K_UP:
            new = max(0, self._manage_sel - 1)
            if new != self._manage_sel:
                self._play("hover")
            self._manage_sel = new
        elif key == pygame.K_DOWN:
            new = min(len(entries) - 1, self._manage_sel + 1)
            if new != self._manage_sel:
                self._play("hover")
            self._manage_sel = new
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._play("confirm")
            self._get_repo().toggle_hidden(entries[self._manage_sel].id)
            self._clamp_list_sel()
        elif key in (pygame.K_ESCAPE, pygame.K_m):
            self._play("cancel")
            self._modal = None

    # ── Edit Tags modal ───────────────────────────────────────

    def _editor_rows(self) -> list[tuple[str, str]]:
        entry = self._selected_entry()
        rows: list[tuple[str, str]] = [("system", t) for t in EDITABLE_SYSTEM_TAGS]
        if entry:
            rows.extend(("custom", t) for t in custom_tags(entry))
        rows.append(("new", ""))
        return rows

    def _open_tags(self) -> None:
        if not self._selected_entry():
            return
        self._modal = M_TAGS
        self._tag_editor_sel = 0
        self._tag_warning = ""
        self._tag_warning_t = 0

    def _set_tag_warning(self, msg: str) -> None:
        self._tag_warning = msg
        self._tag_warning_t = 90  # ~1.5s @60fps

    def _handle_tags_key(self, key: int) -> None:
        rows = self._editor_rows()
        if key == pygame.K_ESCAPE:
            self._play("cancel")
            self._modal = M_ACTION
            self._tag_warning = ""
            self._tag_warning_t = 0
        elif key == pygame.K_UP:
            new = max(0, self._tag_editor_sel - 1)
            if new != self._tag_editor_sel:
                self._play("hover")
            self._tag_editor_sel = new
        elif key == pygame.K_DOWN:
            new = min(len(rows) - 1, self._tag_editor_sel + 1)
            if new != self._tag_editor_sel:
                self._play("hover")
            self._tag_editor_sel = new
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._activate_editor_row(rows[self._tag_editor_sel])

    def _activate_editor_row(self, row: tuple[str, str]) -> None:
        kind, tag = row
        if kind == "new":
            self._play("confirm")
            self._begin_new_tag()
            return
        entry = self._selected_entry()
        if not entry:
            return
        repo = self._get_repo()
        if tag in entry.tags:
            repo.remove_tag(entry.id, tag)
            self._play("cancel")
            return
        if not repo.add_tag(entry.id, tag):
            self._set_tag_warning(f"max tags ({repo.max_tags_per_item}) reached")
            return
        self._play("confirm")

    # ── New custom tag entry ──────────────────────────────────

    def _begin_new_tag(self) -> None:
        entry = self._selected_entry()
        repo = self._get_repo()
        if entry and len(entry.tags) >= repo.max_tags_per_item:
            self._set_tag_warning(f"max tags ({repo.max_tags_per_item}) reached")
            return
        self._modal = M_NEWTAG
        self._tag_input = ""
        pygame.key.start_text_input()

    def _end_new_tag(self) -> None:
        pygame.key.stop_text_input()
        self._modal = M_TAGS
        self._tag_input = ""

    def _handle_new_tag_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.TEXTINPUT:
            if len(self._tag_input) < CUSTOM_TAG_MAX_LEN:
                self._tag_input += event.text
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_BACKSPACE:
            self._tag_input = self._tag_input[:-1]
        elif event.key == pygame.K_ESCAPE:
            self._play("cancel")
            self._end_new_tag()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._commit_new_tag()

    def _commit_new_tag(self) -> None:
        tag = normalize_custom_tag(self._tag_input)
        if not tag:
            self._set_tag_warning("invalid tag")
            return
        entry = self._selected_entry()
        if not entry:
            self._end_new_tag()
            return
        if tag in entry.tags:
            self._set_tag_warning("tag already added")
            return
        if not self._get_repo().add_tag(entry.id, tag):
            self._set_tag_warning(
                f"max tags ({self._get_repo().max_tags_per_item}) reached")
            return
        self._play("confirm")
        self._end_new_tag()

    # ── Update / Render ───────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._tag_warning_t > 0:
            self._tag_warning_t -= 1
            if self._tag_warning_t == 0:
                self._tag_warning = ""

    def render(self, screen: pygame.Surface) -> None:
        self._renderer.render(
            screen,
            gp=self._get_repo().gp,
            page_id=self.page_id,
            tab_index=self._tab_index,
            tab_counts=[
                len(filtered_items(self._get_repo(), i, self._mc_catalog))
                for i in range(len(TABS))
            ],
            items=self._filtered_items(),
            list_sel=self._list_sel,
            selected_entry=self._selected_entry(),
            modal=self._modal,
            action_options=(
                self._action_options(self._selected_entry())
                if self._selected_entry() else []
            ),
            action_sel=self._action_sel,
            discard_qty=self._discard_qty,
            manage_entries=self._manage_entries(),
            manage_sel=self._manage_sel,
            hidden_ids=self._get_repo().hidden_ids,
            editor_rows=self._editor_rows() if self._modal in (M_TAGS, M_NEWTAG) else [],
            editor_sel=self._tag_editor_sel,
            tag_warning=self._tag_warning,
            tag_input=self._tag_input,
            target_overlay=self._target_overlay,
        )
