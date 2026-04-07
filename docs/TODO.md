# V1 Deliverables

## Reorganize modules

Goal: eliminate the `core/` wrapper (it adds depth without meaning), rename `data/` → `io/`, introduce `dto/` for immutable data objects, and `util/` for small utilities.

### 1. Flatten `core/` — remove the wrapper

`core/` groups nearly everything, which means it groups nothing. Promote its children directly under `engine/`:
- `core/app_module.py` → `engine/app_module.py`
- `core/game.py` → `engine/game.py`
- `core/battle/` → `engine/battle/`
- `core/dialogue/` → `engine/dialogue/`
- `core/encounter/` → `engine/encounter/`
- `core/item/` → `engine/item/`
- `core/state/` → `engine/state/`
- `core/scenes/` → `engine/scenes/`
- `core/debug/` → `engine/debug/`

Loose files in `core/` (`scene.py`, `scene_manager.py`, `scene_registry.py`, `display.py`, `settings.py`, `frame_clock.py`) move to their new homes per steps below.

Delete `core/` when empty.

### 2. Merge `settings.py` + `config/engine_settings.py`

`settings.py` holds compile-time constants (screen size, FPS, tile size).
`config/engine_settings.py` loads runtime settings from `config/settings.yaml`.
Merge both into `engine/settings.py` as a single `Settings` class — constants as class attrs, runtime overrides loaded from YAML. Delete the `config/` subfolder.

### 3. Introduce `engine/dto/` for immutable data objects

Pure data containers with no behavior beyond accessors. Move or convert to frozen:
- `models/position.py` → `dto/position.py` (already immutable via `__slots__` + `__setattr__`)
- `models/save_slot.py` → `dto/save_slot.py` (make frozen)
- `encounter/encounter_zone.py` — split: DTOs (`Formation`, `EncounterSet`, `BossConfig`, `BarrierEnemy`, `EncounterZone`) → `dto/encounter_zone.py`; loader function `load_encounter_zone()` → `io/encounter_zone_loader.py`
- `battle/battle_rewards.py` — split: DTOs (`LevelUpResult`, `MemberExpResult`, `LootResult`, `BattleRewards`) → `dto/battle_rewards.py`; `RewardCalculator` stays in `battle/`
- `item/item_effect_handler.py` — split: DTOs (`FieldItemDef`, `UseResult`) → `dto/item_defs.py`; `ItemEffectHandler` stays in `item/`
- `world/portal.py` → `dto/portal.py` (pure data + trivial geometry check)

Not DTOs — these are mutable runtime state and stay where they are:
- `battle/combatant.py` — mutable (HP changes during battle)
- `battle/battle_state.py` — mutable (phase transitions, turn tracking)

### 4. Introduce `engine/util/` for small utilities

- `models/clock.py` → `util/clock.py` (Clock protocol + SystemClock + FakeClock)
- `core/frame_clock.py` → `util/frame_clock.py` (pygame timing wrapper)
- `state/playtime.py` → `util/playtime.py` (session time accumulator)

Delete `models/` when empty.

### 5. Rename `data/` → `io/`

`io` is not a Python keyword. As a subpackage (`engine.io`), it won't shadow the stdlib `io` module. Rename and consolidate all file-I/O classes here:
- `data/loader.py` → `io/manifest_loader.py` (rename for clarity)
- `core/state/game_state_manager.py` → `io/save_manager.py`
- `core/encounter/enemy_loader.py` → `io/enemy_loader.py`
- `core/item/item_catalog.py` → `io/item_catalog.py`
- `core/dialogue/dialogue_engine.py` — extract file-loading into `io/dialogue_loader.py`; runtime walker stays in `dialogue/`
- `world/npc_loader.py` → `io/npc_loader.py`
- `world/portal_loader.py` → `io/portal_loader.py`
- New: `io/encounter_zone_loader.py` (from encounter_zone.py split, see step 3)

### 6. Move renderers and UI helpers into `engine/ui/`

Currently `engine/ui/` only has `menu.py`. Move rendering-only files there:
- `scenes/battle_renderer.py` → `ui/battle_renderer.py`
- `scenes/item_renderer.py` → `ui/item_renderer.py`
- `scenes/status_renderer.py` → `ui/status_renderer.py`
- `scenes/target_select_overlay.py` → `ui/target_select_overlay.py`
- `core/display.py` → `ui/display.py`

### 7. Extract logic files out of `scenes/`

`*_logic.py` files contain domain logic, not scene lifecycle. Move to topical subfolders:
- `scenes/battle_logic.py` → `battle/battle_logic.py`
- `scenes/item_logic.py` → `item/item_logic.py`
- `scenes/status_logic.py` → `state/status_logic.py`
- `scenes/world_map_logic.py` → `world/world_map_logic.py`

### 8. Group scene infrastructure into `scenes/`

Move loose scene infra files into `engine/scenes/`:
- `core/scene.py` → `scenes/scene.py`
- `core/scene_manager.py` → `scenes/scene_manager.py`
- `core/scene_registry.py` → `scenes/scene_registry.py`

### Resulting structure (summary)

```
engine/
  main.py
  app_module.py
  game.py
  settings.py              # merged Settings + EngineSettings
  dto/
    position.py
    save_slot.py
    portal.py
    encounter_zone.py      # Formation, EncounterSet, BossConfig, etc.
    battle_rewards.py      # LevelUpResult, MemberExpResult, LootResult, etc.
    item_defs.py           # FieldItemDef, UseResult
  util/
    clock.py               # Clock protocol, SystemClock, FakeClock
    frame_clock.py
    playtime.py
  io/
    manifest_loader.py
    save_manager.py
    enemy_loader.py
    encounter_zone_loader.py
    item_catalog.py
    dialogue_loader.py
    npc_loader.py
    portal_loader.py
  scenes/
    scene.py               # base class
    scene_manager.py
    scene_registry.py
    battle_scene.py
    dialogue_scene.py
    world_map_scene.py
    ... (all *_scene.py)
  ui/
    display.py
    menu.py
    battle_renderer.py
    item_renderer.py
    status_renderer.py
    target_select_overlay.py
  battle/
    battle_logic.py
    battle_rewards.py      # RewardCalculator (logic, not DTO)
    battle_state.py
    combatant.py
  dialogue/
    dialogue_engine.py     # runtime dialogue tree walker (no I/O)
  encounter/
    encounter_manager.py
    encounter_resolver.py
  item/
    item_effect_handler.py # handler class only, DTOs moved to dto/
    item_logic.py
  state/
    flag_state.py
    game_state.py
    game_state_holder.py
    map_state.py
    party_state.py
    repository_state.py
    status_logic.py
  debug/
    debug_bootstrap.py
  world/
    animation_controller.py
    camera.py
    collision.py
    npc.py
    player.py
    sprite_sheet.py
    tile_map.py
    tile_map_factory.py
    world_map_logic.py
```

### Execution notes
- Step 1 (flatten `core/`) touches the most imports — do it first, run tests.
- Then do remaining steps one at a time, updating imports and `app_module.py` after each.
- Run `python -m pytest` after each step to catch broken imports.
- For DTO splits (step 3), keep re-exports in the original module temporarily if needed to avoid a big-bang import change.
- Update `CLAUDE.md` architecture section when done.

## Bugs

## Unstub

### Battle — Enemy Sprites
- **Enemy sprite_id placeholder** — `combatant.py:36` `sprite_id` defaults to empty string; enemies render as colored rectangles, not sprites

## Feature
- Boss encounters + story act transitions | Story progression
- Party join flow | Full party
- Full playthrough pass | End-to-end
