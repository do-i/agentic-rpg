# Refactor Phase 1: Regroup Engine Files by Feature Domain

## Current State

```
engine/
  battle/          combatant, battle_state, battle_logic, battle_rewards, constants
  dialogue/        dialogue_engine
  encounter/       encounter_manager, encounter_resolver, encounter_zone
  item/            item_effect_handler, item_logic
  world/           animation_controller, camera, collision, npc, player,
                   sprite_sheet, tile_map, tile_map_factory, world_map_logic
  audio/           bgm_manager
  debug/           debug_bootstrap
  dto/             13 data-container modules (position, game_state, member_state, ...)
  io/              8 loaders (save_manager, enemy_loader, item_catalog, ...)
  scenes/          20 scene files (all domains mixed together)
  service/         party_state, repository_state, status_logic
  ui/              battle_renderer, item_renderer, status_renderer,
                   target_select_overlay, menu, display, colors
  util/            clock, frame_clock, playtime
  app_module.py, game.py, main.py, settings.py
```

**Problems:**
- `scenes/` is a grab-bag of 20 files spanning 8+ domains
- `ui/` mixes domain-specific renderers with shared widgets
- `io/` mixes domain-specific loaders with cross-cutting persistence
- `service/` mixes domain-specific logic with shared services
- Finding all battle-related code requires checking 5 directories

---

## Proposed Structure

```
engine/
  common/
    __init__.py
    battle_rewards_data.py   # <-- from dto/battle_rewards.py (immutable)
    encounter_zone_data.py   # <-- from dto/encounter_zone.py (immutable)
    flag_state.py            # <-- from dto/ (mutable, already _state)
    game_state.py            # <-- from dto/ (mutable, already _state)
    game_state_holder.py     # <-- from dto/ (mutable, already _state)
    item_defs_data.py        # <-- from dto/item_defs.py (immutable)
    item_entry_state.py      # <-- from dto/item_entry.py (mutable)
    map_state.py             # <-- from dto/ (mutable, already _state)
    member_state.py          # <-- from dto/ (mutable, already _state)
    party_state.py           # <-- from dto/ (mutable, already _state)
    position_data.py         # <-- from dto/position.py (immutable)
    portal_data.py           # <-- from dto/portal.py (immutable)
    save_slot_data.py        # <-- from dto/save_slot.py (immutable)
    service/                 # shared business logic
      __init__.py
      party_state.py         # used by battle, encounter, status, io, debug
      repository_state.py    # used by item, encounter, dialogue, shop, dto
    ui/                      # shared rendering / widgets
      __init__.py
      colors.py
      display.py
      menu.py
      target_select_overlay.py
    scene/                   # scene infrastructure
      __init__.py
      scene.py
      scene_manager.py
      scene_registry.py
    io/                      # cross-cutting persistence
      __init__.py
      manifest_loader.py
      save_manager.py
      game_state_loader.py
    util/                    # (moved as-is)
      __init__.py
      clock.py
      frame_clock.py
      playtime.py

  battle/
    __init__.py
    combatant.py             # (existing)
    battle_state.py          # (existing)
    battle_logic.py          # (existing)
    battle_rewards.py        # (existing)
    constants.py             # (existing)
    battle_scene.py          # <-- from scenes/
    post_battle_scene.py     # <-- from scenes/
    game_over_scene.py       # <-- from scenes/
    battle_renderer.py       # <-- from ui/
    enemy_loader.py          # <-- from io/

  dialogue/
    __init__.py
    dialogue_engine.py       # (existing)
    dialogue_scene.py        # <-- from scenes/

  encounter/
    __init__.py
    encounter_manager.py     # (existing)
    encounter_resolver.py    # (existing)
    encounter_zone.py        # (existing)
    encounter_zone_loader.py # <-- from io/

  inn/                       # (new domain folder)
    __init__.py
    inn_scene.py             # <-- from scenes/

  item/
    __init__.py
    item_effect_handler.py   # (existing)
    item_logic.py            # (existing)
    item_scene.py            # <-- from scenes/
    item_renderer.py         # <-- from ui/
    item_catalog.py          # <-- from io/

  shop/                      # (new domain folder)
    __init__.py
    item_shop_scene.py       # <-- from scenes/
    apothecary_scene.py      # <-- from scenes/
    magic_core_shop_scene.py # <-- from scenes/

  status/                    # (new domain folder)
    __init__.py
    status_scene.py          # <-- from scenes/
    status_renderer.py       # <-- from ui/
    status_logic.py          # <-- from service/

  title/                     # (new domain folder)
    __init__.py
    title_scene.py           # <-- from scenes/
    boot_scene.py            # <-- from scenes/
    name_entry_scene.py      # <-- from scenes/
    load_game_scene.py       # <-- from scenes/
    save_modal_scene.py      # <-- from scenes/

  world/
    __init__.py
    animation_controller.py  # (existing)
    camera.py                # (existing)
    collision.py             # (existing)
    npc.py                   # (existing)
    player.py                # (existing)
    sprite_sheet.py          # (existing)
    tile_map.py              # (existing)
    tile_map_factory.py      # (existing)
    world_map_logic.py       # (existing)
    world_map_scene.py       # <-- from scenes/
    npc_loader.py            # <-- from io/
    portal_loader.py         # <-- from io/

  audio/                     # (unchanged)
    __init__.py
    bgm_manager.py

  debug/                     # (unchanged)
    __init__.py
    debug_bootstrap.py

  app_module.py              # (stays, imports updated)
  game.py                    # (stays, imports updated)
  main.py                    # (stays)
  settings.py                # (stays)
```

---

## File Move Mapping

### scenes/ (20 files -> dissolved)

| Current Path | New Path | Rationale |
|---|---|---|
| scenes/scene.py | common/scene/scene.py | Base class, used everywhere |
| scenes/scene_manager.py | common/scene/scene_manager.py | Infrastructure |
| scenes/scene_registry.py | common/scene/scene_registry.py | Infrastructure |
| scenes/battle_scene.py | battle/battle_scene.py | Primary domain: battle |
| scenes/post_battle_scene.py | battle/post_battle_scene.py | Battle reward flow |
| scenes/game_over_scene.py | battle/game_over_scene.py | Triggered by battle loss |
| scenes/dialogue_scene.py | dialogue/dialogue_scene.py | Primary domain: dialogue |
| scenes/inn_scene.py | inn/inn_scene.py | Primary domain: inn |
| scenes/item_scene.py | item/item_scene.py | Primary domain: item |
| scenes/item_shop_scene.py | shop/item_shop_scene.py | Primary domain: shop |
| scenes/apothecary_scene.py | shop/apothecary_scene.py | Primary domain: shop |
| scenes/magic_core_shop_scene.py | shop/magic_core_shop_scene.py | Primary domain: shop |
| scenes/status_scene.py | status/status_scene.py | Primary domain: status |
| scenes/title_scene.py | title/title_scene.py | Title/menu flow |
| scenes/boot_scene.py | title/boot_scene.py | Title/menu flow |
| scenes/name_entry_scene.py | title/name_entry_scene.py | Title/menu flow (new game) |
| scenes/load_game_scene.py | title/load_game_scene.py | Title/menu flow (load game) |
| scenes/save_modal_scene.py | title/save_modal_scene.py | Save/load flow |
| scenes/world_map_scene.py | world/world_map_scene.py | Primary domain: world |

### ui/ (7 files -> dissolved)

| Current Path | New Path | Rationale |
|---|---|---|
| ui/display.py | common/ui/display.py | Shared infrastructure |
| ui/menu.py | common/ui/menu.py | Shared widget |
| ui/colors.py | common/ui/colors.py | Shared constants |
| ui/target_select_overlay.py | common/ui/target_select_overlay.py | Shared overlay (item + status) |
| ui/battle_renderer.py | battle/battle_renderer.py | Battle-only |
| ui/item_renderer.py | item/item_renderer.py | Item-only |
| ui/status_renderer.py | status/status_renderer.py | Status-only |

### io/ (8 files -> split)

| Current Path | New Path | Rationale |
|---|---|---|
| io/manifest_loader.py | common/io/manifest_loader.py | Cross-cutting |
| io/save_manager.py | common/io/save_manager.py | Cross-cutting |
| io/game_state_loader.py | common/io/game_state_loader.py | Cross-cutting |
| io/enemy_loader.py | battle/enemy_loader.py | Battle-only |
| io/item_catalog.py | item/item_catalog.py | Item-only |
| io/npc_loader.py | world/npc_loader.py | World-only |
| io/portal_loader.py | world/portal_loader.py | World-only |
| io/encounter_zone_loader.py | encounter/encounter_zone_loader.py | Encounter-only |

### service/ (3 files -> split)

| Current Path | New Path | Rationale |
|---|---|---|
| service/party_state.py | common/service/party_state.py | Used by 5+ domains |
| service/repository_state.py | common/service/repository_state.py | Used by 5+ domains |
| service/status_logic.py | status/status_logic.py | Status-only |

### dto/ (13 files -> flattened into common/)

All dto files move directly into `common/` (no `common/dto/` subdirectory). Every dto module is imported by 3+ domains -- none are domain-specific enough to colocate.

Suffix convention applied consistently:
- `_data` : immutable containers
- `_state`: mutable containers

| Current Path | New Path | Rationale |
|---|---|---|
| dto/position.py | common/position_data.py | Immutable value object |
| dto/portal.py | common/portal_data.py | Immutable map exit definition |
| dto/encounter_zone.py | common/encounter_zone_data.py | Immutable formation/zone defs |
| dto/item_defs.py | common/item_defs_data.py | Immutable field-use definitions |
| dto/battle_rewards.py | common/battle_rewards_data.py | Immutable reward/level-up results |
| dto/save_slot.py | common/save_slot_data.py | Immutable save file metadata |
| dto/item_entry.py | common/item_entry_state.py | Mutable inventory stack (qty changes) |
| dto/flag_state.py | common/flag_state.py | Mutable, already `_state` |
| dto/map_state.py | common/map_state.py | Mutable, already `_state` |
| dto/game_state.py | common/game_state.py | Mutable, already `_state` |
| dto/game_state_holder.py | common/game_state_holder.py | Mutable runtime holder |
| dto/member_state.py | common/member_state.py | Mutable, already `_state` |
| dto/party_state.py | common/party_state.py | Mutable, already `_state` |

### util/ (3 files -> moved to common/util/)

All util files move to `common/util/`. Pure infrastructure.

---

## Classification Criteria

A file was assigned to a **feature folder** when:
1. It primarily serves one domain (>80% of its logic is domain-specific)
2. Its name implies domain ownership (e.g., `battle_renderer`, `enemy_loader`)
3. Its importers are predominantly within that domain or are the domain's scene

A file was assigned to **common/** when:
1. It is imported by 3+ feature domains
2. It provides infrastructure (scene base class, display, clock)
3. It is a data container used across domain boundaries (all dto modules)

---

## Import Update Examples

### Before
```python
# In battle/battle_scene.py (currently scenes/battle_scene.py)
from engine.scenes.scene import Scene
from engine.scenes.scene_registry import SceneRegistry
from engine.ui.battle_renderer import BattleRenderer
from engine.dto.game_state_holder import GameStateHolder
from engine.dto.position import Position
from engine.io.save_manager import SaveManager
```

### After
```python
from engine.common.scene.scene import Scene
from engine.common.scene.scene_registry import SceneRegistry
from engine.battle.battle_renderer import BattleRenderer
from engine.common.game_state_holder import GameStateHolder
from engine.common.position_data import Position
from engine.common.io.save_manager import SaveManager
```

### Before
```python
# In encounter/encounter_resolver.py
from engine.io.enemy_loader import EnemyLoader
from engine.encounter.encounter_zone import EncounterZone
from engine.dto.encounter_zone import Formation
```

### After
```python
from engine.battle.enemy_loader import EnemyLoader
from engine.encounter.encounter_zone import EncounterZone  # unchanged
from engine.common.encounter_zone_data import Formation
```

---

## Migration Order

Execute in this order to minimize breakage at each step. Run tests after each step.

### Step 1: Create common/ skeleton and move infrastructure

Move files that everything depends on first. No domain logic changes.

1. `dto/` -> `common/` (flat, with _data/_state renames per table above)
2. `util/` -> `common/util/`
3. `service/party_state.py` -> `common/service/party_state.py`
4. `service/repository_state.py` -> `common/service/repository_state.py`
5. `scenes/scene.py` -> `common/scene/scene.py`
6. `scenes/scene_manager.py` -> `common/scene/scene_manager.py`
7. `scenes/scene_registry.py` -> `common/scene/scene_registry.py`
8. `ui/display.py`, `ui/menu.py`, `ui/colors.py`, `ui/target_select_overlay.py` -> `common/ui/`
9. `io/manifest_loader.py`, `io/save_manager.py`, `io/game_state_loader.py` -> `common/io/`

**Import updates:** Every file in the project that imports from dto, util, service (shared), scenes (infra), ui (shared), or io (shared).

### Step 2: Move domain-specific loaders into their domains

10. `io/enemy_loader.py` -> `battle/enemy_loader.py`
11. `io/item_catalog.py` -> `item/item_catalog.py`
12. `io/npc_loader.py` -> `world/npc_loader.py`
13. `io/portal_loader.py` -> `world/portal_loader.py`
14. `io/encounter_zone_loader.py` -> `encounter/encounter_zone_loader.py`

**Import updates:** Fewer files affected -- only the direct consumers of each loader.

### Step 3: Move domain-specific renderers into their domains

15. `ui/battle_renderer.py` -> `battle/battle_renderer.py`
16. `ui/item_renderer.py` -> `item/item_renderer.py`
17. `ui/status_renderer.py` -> `status/status_renderer.py`

### Step 4: Move domain-specific service into its domain

18. `service/status_logic.py` -> `status/status_logic.py`

### Step 5: Dissolve scenes/ into domain folders

Largest step. Move each scene to its owning domain.

19. `scenes/battle_scene.py` -> `battle/`
20. `scenes/post_battle_scene.py` -> `battle/`
21. `scenes/game_over_scene.py` -> `battle/`
22. `scenes/dialogue_scene.py` -> `dialogue/`
23. `scenes/inn_scene.py` -> `inn/` (new)
24. `scenes/item_scene.py` -> `item/`
25. `scenes/item_shop_scene.py` -> `shop/` (new)
26. `scenes/apothecary_scene.py` -> `shop/`
27. `scenes/magic_core_shop_scene.py` -> `shop/`
28. `scenes/status_scene.py` -> `status/` (new)
29. `scenes/world_map_scene.py` -> `world/`
30. `scenes/title_scene.py` -> `title/` (new)
31. `scenes/boot_scene.py` -> `title/`
32. `scenes/name_entry_scene.py` -> `title/`
33. `scenes/load_game_scene.py` -> `title/`
34. `scenes/save_modal_scene.py` -> `title/`

### Step 6: Clean up

35. Delete empty `scenes/`, `dto`, `ui/`, `io/`, `service/` directories
36. Update `app_module.py` imports (heaviest single file -- touches all domains)
37. Update test imports
38. Final full test run

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Circular imports between domains | dto stays in common/ as a neutral layer; domains import from common/, not from each other's internals |
| Large import-update diff | Scriptable with sed/IDE refactor; all changes are mechanical path swaps |
| `app_module.py` is a mega-hub | It already imports from everywhere; paths change but structure doesn't |
| `world_map_scene.py` imports 10+ domains | Remains unchanged in logic; only import paths shift |
| Tests break from import changes | Run `pytest` after each migration step; import errors are immediate and obvious |

---

## Out of Scope (per constraints)

- Splitting large files (e.g., world_map_scene.py)
- Introducing facades or re-export `__init__.py` modules
- Rewriting any internal logic
- Changing class names or function signatures
- Adding new abstractions
