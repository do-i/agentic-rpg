---
name: verify
description: Drive the JRPG headlessly and capture screenshots to verify engine/scenario changes at the rendered surface. Use when a change needs runtime observation (shops, dialogue, menus, scenes) rather than unit tests.
---

# Verify — headless game driving

The game is pygame; its surface is pixels. There is no windowing in this
environment, so drive the real scenes headlessly with the SDL dummy drivers
and capture screenshots with `pygame.image.save`.

## Recipe

Build a harness script (put it in `$CLAUDE_JOB_DIR/tmp/`) that mirrors
`engine/main.py`'s bootstrapping, then pump the same
handle_events/update/render loop `Game.run()` uses:

```python
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from injector import Injector
from engine.app_module import AppModule
# ... see the imports in the harness body below

pygame.init()
inj = Injector([AppModule(scenario_path=".../rusted_kingdoms",
                          mode="normal", recording_file="/tmp/unused.pkl",
                          playback_speed=1.0, seed=7)])
cfg = inj.get(EngineConfigData)
screen = pygame.display.set_mode((cfg.screen_width, cfg.screen_height))
inj.get(FontProvider)                 # MUST touch before any render (init_fonts)
registry = inj.get(SceneRegistry)     # builds scenes + theme assets
sm, holder = inj.get(SceneManager), inj.get(GameStateHolder)

state = from_new_game(loader.load(), "Aric",
                      loader.scenario_path / "data" / "classes",
                      loader.scenario_path, inj.get(ItemCatalog))
state.map.move_to(map_id=..., position=Position.from_list([x, y]), facing=...)
holder.set(state)
sm.switch(registry.get("world_map"))

def key(k): sm.handle_events([pygame.event.Event(pygame.KEYDOWN, key=k, mod=0)])
def frames(n):
    for _ in range(n):
        sm.update(1/60); sm.render(screen)
def shot(name): pygame.image.save(screen, f"{OUT}/{name}.png")
```

Run with the venv python: `.venv/bin/python <harness>.py`.

## Gotchas

- **Fade-in swallows input.** After entering a map the world map runs a
  ~1s fade; keys during it are ignored. `frames(70)` first, or poll:
  send RETURN + `frames(10)` in a loop until `wm._overlays.dialogue` is set.
- **Reposition/teleport**: mimic `_apply_transition`'s reset on the
  world_map singleton — set `_tile_map`, `_player`, `_enemy_spawner` to
  None and `_last_controlled_member_id = ""`, update `state.map.move_to`,
  then `frames(70)`.
- **Poll overlay state, don't count frames** for flows: `wm._overlays.dialogue`,
  `wm._overlays.item_shop`, etc. tell you where the UI actually is.
- **Typewriter text**: dialogue reveals ~60 chars/s; `frames(150)` before
  screenshotting a dialogue line.
- New game starts with 0 GP — `state.repository.add_gp(...)` to test buying.
- Useful driving keys: RETURN interact/confirm, ESC cancel/close,
  M field menu, arrows navigate.

## Flows worth driving

- Shop: stand next to keeper (interaction_range 2.5 tiles), RETURN through
  dialogue, buy something, assert `holder.get().repository.gp` and `.items`.
- Field menu: M → arrows → ENTER into sub-scenes; ESC returns.
- Shop interiors are 16x11 with keepers on the counter row y=3; the
  walkable pockets flanking the counter are around [3,3] and [12,4].
