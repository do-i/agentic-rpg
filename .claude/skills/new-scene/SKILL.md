---
name: new-scene
description: This skill should be used when the user wants to "add a scene", "create a new scene", "scaffold a scene", "add a crafting scene", "add a party management scene", "add a fast travel scene", or any request to create a new screen or UI flow in the JRPG engine. Generates the scene class, wires it into AppModule and SceneRegistry, and explains singleton vs factory registration.
version: 0.1.0
---

# New Scene — JRPG Engine

Scaffold a new scene class and wire it into the engine in three files.

## The Three Files to Touch

1. **`engine/<module>/<name>_scene.py`** — the scene class itself
2. **`engine/app_module.py`** — add import + register in `provide_scene_registry`

That's it. No manifest change, no other registry.

## Decide: Singleton or Factory?

| Use `register_singleton` | Use `register_factory` |
|---|---|
| Holds persistent state across visits (world_map, boot) | Fresh instance each time it opens (menus, shops, overlays) |
| Expensive to reconstruct (tile maps, asset loaders) | Needs constructor args that vary per call |
| Only one instance ever makes sense | Dialogue, battle, inn — context changes each open |

Most new menu/overlay scenes should be **factory**.

## Decide: Overlay or Full Scene?

**Overlay** — draws on top of the current scene (dim background + modal box). Takes an `on_close: callable` parameter; calls it to return to the previous scene. Examples: `InnScene`, `ItemShopScene`, `ItemScene`.

**Full scene** — replaces the current scene entirely. No `on_close`. Navigates forward/back via `scene_manager.switch(registry.get("other_scene"))`. Examples: `TitleScene`, `WorldMapScene`, `BattleScene`.

## Workflow

1. Clarify scene purpose, name, and whether it's an overlay or full scene.
2. Determine what dependencies it needs (holder, scene_manager, registry, item_catalog, etc.).
3. Generate the scene class file.
4. Generate the AppModule import and registration snippet.
5. Note any callers that need to open the scene (e.g. which existing scene should push to it).

## Naming Convention

- File: `engine/<module>/<snake_name>_scene.py`
- Class: `<PascalName>Scene`
- Registry key: `"<snake_name>"` (e.g. `"crafting"`, `"party_order"`)
- Module dir: create `engine/<module>/` if it doesn't exist (add empty `__init__.py`)

## Scene Class Template

```python
from __future__ import annotations

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder

# ── Colors ────────────────────────────────────────────────────
C_BG     = (18, 18, 35)
C_BORDER = (160, 160, 100)
C_HEADER = (220, 220, 180)
C_TEXT   = (238, 238, 238)
C_MUTED  = (130, 130, 140)
C_HINT   = (100, 100, 115)

# ── Layout ────────────────────────────────────────────────────
MODAL_W  = 520
PAD      = 24
HEADER_H = 48
FOOTER_H = 36


class <PascalName>Scene(Scene):

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,          # remove if full scene, not overlay
        sfx_manager=None,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close   # remove if full scene
        self._sfx_manager   = sfx_manager
        self._fonts_ready   = False

    # ── Lazy font init (call once, first render) ───────────────

    def _init_fonts(self) -> None:
        self._font_title = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_body  = pygame.font.SysFont("Arial", 16)
        self._font_hint  = pygame.font.SysFont("Arial", 15)
        self._fonts_ready = True

    # ── Input ─────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_close()   # or: self._scene_manager.switch(self._registry.get("world_map"))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        # dim overlay (remove for full scenes)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        mh = HEADER_H + 200 + FOOTER_H
        mx = (screen.get_width()  - MODAL_W) // 2
        my = (screen.get_height() - mh) // 2

        pygame.draw.rect(screen, C_BG,     (mx, my, MODAL_W, mh), border_radius=8)
        pygame.draw.rect(screen, C_BORDER, (mx, my, MODAL_W, mh), 2, border_radius=8)

        self._draw_header(screen, mx, my)
        self._draw_footer(screen, mx, my + mh - FOOTER_H)

    def _draw_header(self, screen: pygame.Surface, mx: int, my: int) -> None:
        title = self._font_title.render("<Scene Title>", True, C_HEADER)
        screen.blit(title, (mx + PAD, my + (HEADER_H - title.get_height()) // 2))

    def _draw_footer(self, screen: pygame.Surface, mx: int, y: int) -> None:
        pygame.draw.line(screen, (50, 50, 70), (mx + 10, y), (mx + MODAL_W - 10, y))
        hint = self._font_hint.render("ESC  close", True, C_HINT)
        screen.blit(hint, (mx + PAD, y + (FOOTER_H - hint.get_height()) // 2))
```

## AppModule Wiring

### Import (top of app_module.py)
```python
from engine.<module>.<name>_scene import <PascalName>Scene
```

### Factory registration (inside `provide_scene_registry`, before `return registry`)
```python
registry.register_factory("<snake_name>",
    lambda: <PascalName>Scene(
        holder=holder,
        scene_manager=scene_manager,
        registry=registry,
        on_close=lambda: scene_manager.switch(registry.get("world_map")),
        sfx_manager=sfx_manager,
    ))
```

### Singleton registration (use only if scene holds persistent state)
```python
registry.register_singleton("<snake_name>", <PascalName>Scene(
    holder=holder,
    scene_manager=scene_manager,
    registry=registry,
    sfx_manager=sfx_manager,
))
```

## Opening the Scene from Another Scene

To push to the new scene from (e.g.) `WorldMapScene` or a dialogue `on_complete`:

```python
# From Python code:
self._scene_manager.switch(self._registry.get("<snake_name>"))

# As a factory with a custom on_close:
scene = <PascalName>Scene(
    ...,
    on_close=lambda: self._scene_manager.switch(self._registry.get("world_map")),
)
self._scene_manager.switch(scene)
```

If registered as a factory in AppModule, `registry.get("<snake_name>")` creates a fresh instance each call — which is correct for overlays.

## Additional Resources

- **`references/scene-patterns.md`** — patterns for menus with cursor/selection, multi-page lists, confirmation dialogs, and toast notifications
