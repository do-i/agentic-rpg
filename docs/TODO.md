# V1 Deliverables

## Bugs

### Inn
- ~~After resting at Inn, player position is not on the same tile as before. — ✅ `_open_inn()` now calls `state.map.set_position()` before opening the overlay, matching the pattern used by save modal and portal transitions.~~


## Unstub

### Battle — Items
- ~~**Hardcoded item menu** — ✅ `_open_item_menu()` now reads real items from party repository via `ItemEffectHandler`~~
- ~~**Items always heal 100 HP** — ✅ `resolve_action()` item branch now uses `ItemEffectHandler._apply_to_member()` for correct effects (restore_hp, restore_mp, restore_full, cure, revive)~~

### Battle — Flee
- ~~**Run always succeeds** — ✅ `attempt_flee()` in `battle_logic.py` now uses flee formula (base 30% + 2% per Rogue DEX), boss battles block flee, failed flee consumes the turn~~

### Battle — Game Over
- **No Game Over screen** — `battle_scene.py:31` on defeat, silently returns to world map; should show a Game Over scene with restart/load/quit options

### Battle — Loot
- ~~**Loot table stub** — ✅ `_resolve_loot()` now reads `drops.mc` (guaranteed magic cores, aggregated by size) and `drops.loot` (weighted item pools via `_weighted_pick()`) from enemy YAML; item drops added to repository on victory~~

### Battle — Enemy AI
- ~~**Enemy abilities not loaded** — ✅ `EnemyLoader` now loads inline `ai:`/`targeting:` blocks and external `ai_ref:` files into `Combatant.ai_data`. `pick_enemy_action()` supports random and conditional patterns (hp_pct_below, turn_mod). `resolve_enemy_turn()` uses weighted action selection and targeting (random_alive, lowest_hp, highest_hp, all_party, self).~~
- ~~**Barrier blocked message not shown** — ✅ `encounter_resolver._build_enemies()` now collects `barrier_messages` onto `BattleState`; `BattleScene` displays the first barrier message at battle start.~~

### Battle — Enemy Sprites
- **Enemy sprite_id placeholder** — `combatant.py:36` `sprite_id` defaults to empty string; enemies render as colored rectangles, not sprites

### Dialogue
- **Portrait placeholder** — `dialogue_scene.py:125` draws a colored rect instead of loading character portrait sprites

### Repository / Items
- ~~**Repository is a stub** — ✅ `RepositoryState` now supports sell, tag editing (add/remove with max-5 guardrail), lock/unlock, `items_by_tag()` filtering, and `remove_item()`. `ItemCatalog` loads all scenario YAML and auto-populates metadata on `add_item()`.~~
- ~~**Debug item repository** — ✅ `_make_debug_repository()` removed; `ItemScene` always uses real repository from `GameStateHolder`. `debug_items` setting removed.~~

### Magic Core Shop
- ~~**Hardcoded exchange rates** — `magic_core_shop_scene.py:16` `MC_SIZES` list with hardcoded GP-per-unit rates; should load from scenario YAML~~ ✓ loaded from `magic_cores.yaml`
- ~~**Hardcoded MC labels/order** — `item_logic.py:14` `MC_IDS`, `MC_ORDER`, `MC_LABELS` are hardcoded; should derive from item data~~ ✓ replaced with data-driven `MCCatalog`

## Feature
- Use sprite head as protrait in a NPC dialogue
- Party join flow | Full party
- Shop + Apothecary | Buy/craft
- Boss encounters + story act transitions | Story progression
- Full playthrough pass | End-to-end
