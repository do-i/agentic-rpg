# engine/common/wizard_scene.py
#
# Shared base for multi-page picker scenes (equip, spell, ...). Each scene
# is a sequence of named pages; the user navigates UP/DOWN inside a page,
# ENTER advances, ESC/M backs out (and from the first page, closes the
# scene). Subclasses register pages and decide what each ENTER means by
# returning the next page name from `on_confirm` (or None to stay/handle
# inline). Selection state, hover SFX, and the scene-close path live here.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry


@dataclass
class WizardPage:
    """One page in a wizard. Subclasses build these and pass them to
    `WizardScene._register_page`.

    - `name`        — page id, used by other pages' on_confirm/on_back.
    - `count_fn`    — current row count (UP/DOWN clamps against this).
    - `on_confirm`  — called on ENTER. Returns the next page id (or None
                      to stay on this page; the callback can mutate scene
                      state and play its own SFX).
    - `on_back`     — called on ESC/M. Returns the previous page id, or
                      None to close the scene entirely.
    - `selection`   — current row index. Reset to 0 when the page is
                      navigated to via `_navigate`.
    """
    name: str
    count_fn: Callable[[], int]
    on_confirm: Callable[[], str | None]
    on_back: Callable[[], str | None]
    selection: int = 0


class WizardScene(Scene):
    """Base for MEMBER → SLOT/SPELL → DETAIL field menus.

    Subclasses:
      1. Call `_register_page(...)` for each page in their flow (the first
         registered page is the entry point).
      2. Implement `render(screen)` and any per-page rendering.
      3. Override `_is_input_blocked()` / `_handle_blocked_input()` if
         they have modal overlays (target select, popup, ...).

    Subclasses must also call `__init__` with sfx_manager and the scene-
    close return target so this class can wire up the shared close path.
    """

    def __init__(
        self,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        return_scene_name: str,
        sfx_manager,
    ) -> None:
        self._scene_manager = scene_manager
        self._registry = registry
        self._return_scene_name = return_scene_name
        self._sfx_manager = sfx_manager
        self._pages: dict[str, WizardPage] = {}
        self._page_order: list[str] = []
        self._page_id: str = ""

    # ── Page registration ────────────────────────────────────

    def _register_page(self, page: WizardPage) -> None:
        if not self._page_id:
            self._page_id = page.name
        self._pages[page.name] = page
        self._page_order.append(page.name)

    @property
    def page_id(self) -> str:
        return self._page_id

    def _page(self, name: str) -> WizardPage:
        return self._pages[name]

    def _current_page(self) -> WizardPage:
        return self._pages[self._page_id]

    def _navigate(self, target: str | None) -> None:
        """Switch to `target` (resets that page's selection) or close the
        scene if target is None."""
        if target is None:
            self._close_scene()
            return
        if target not in self._pages:
            raise KeyError(f"unknown wizard page: {target!r}")
        self._page_id = target
        self._pages[target].selection = 0

    # ── Scene control ────────────────────────────────────────

    def set_return_scene(self, name: str) -> None:
        self._return_scene_name = name

    def _close_scene(self) -> None:
        self._play("cancel")
        self._scene_manager.switch(self._registry.get(self._return_scene_name))

    # ── SFX + selection tracking ─────────────────────────────

    def _play(self, key: str) -> None:
        self._sfx_manager.play(key)

    def _set_sel(self, page: WizardPage, new: int) -> None:
        if new != page.selection:
            self._play("hover")
        page.selection = new

    # ── Modal-overlay hooks ──────────────────────────────────

    def _is_input_blocked(self) -> bool:
        """Override to return True when a modal overlay should swallow
        input (target overlay, popup, ...). Default: never blocked."""
        return False

    def _handle_blocked_input(self, events: list[pygame.event.Event]) -> None:
        """Override alongside `_is_input_blocked`. Default: no-op."""
        pass

    # ── Default Scene plumbing ───────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self._is_input_blocked():
            self._handle_blocked_input(events)
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            page = self._current_page()
            if event.key in (pygame.K_ESCAPE, pygame.K_m):
                target = page.on_back()
                self._navigate(target)
            elif event.key == pygame.K_UP:
                count = page.count_fn()
                if count > 0:
                    self._set_sel(page, max(0, page.selection - 1))
            elif event.key == pygame.K_DOWN:
                count = page.count_fn()
                if count > 0:
                    self._set_sel(page, min(count - 1, page.selection + 1))
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                count = page.count_fn()
                if count == 0:
                    continue
                target = page.on_confirm()
                if target is not None:
                    self._navigate(target)

    def update(self, delta: float) -> None:
        pass
