# V1 Deliverables

## Bugs

### Inn
- Ater woke up player position is not on the same tile as before.
- NPC close to each other: when player is in a proximity of two NPC, dialogue starts on unexpected NPC. Expected behavior, select NPC closest to the player starts dialogue. if both NPC are in same distance, then pick one facing player is picked. Is there a better solution?

## Unstub

### Battle — Items
- ~~**Hardcoded item menu** — ✅ `_open_item_menu()` now reads real items from party repository via `ItemEffectHandler`~~
- ~~**Items always heal 100 HP** — ✅ `resolve_action()` item branch now uses `ItemEffectHandler._apply_to_member()` for correct effects (restore_hp, restore_mp, restore_full, cure, revive)~~

### Battle — Flee
- **Run always succeeds** — `battle_scene.py:290` `_attempt_run()` immediately switches to world map with no flee formula (DEX check, boss block, etc.)

### Battle — Game Over
- **No Game Over screen** — `battle_scene.py:31` on defeat, silently returns to world map; should show a Game Over scene with restart/load/quit options

### Battle — Loot
- **Loot table stub** — `battle_rewards.py:54,165` `LootResult` and `_roll_loot()` always drop 1x Magic Core (S) per enemy; should use weighted loot tables from enemy YAML definitions

### Battle — Enemy AI
- **Enemy abilities not loaded** — `enemy_loader.py:91` `_load_class_abilities()` returns `[]`; enemies only use basic attacks. Should resolve abilities from `ai:` block in enemy YAML
- **Barrier blocked message not shown** — `encounter_resolver.py:125` barrier filtering works but the `blocked_message` is never surfaced in battle UI

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
