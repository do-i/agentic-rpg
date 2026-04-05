# V1 Deliverables

## Bugs

### Inn
Ater woke up player position is not on the same tile as before.


## Unstub

### Battle — Items
- ~~**Hardcoded item menu**~~ — ✅ `_open_item_menu()` now reads real items from party repository via `ItemEffectHandler`
- ~~**Items always heal 100 HP**~~ — ✅ `resolve_action()` item branch now uses `ItemEffectHandler._apply_to_member()` for correct effects (restore_hp, restore_mp, restore_full, cure, revive)

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
- **Repository is a stub** — `repository_state.py:12,32` basic item stack + GP pool only; no sell, no tag editing, no advanced filtering
- **Debug item repository** — `item_scene.py:24` `_make_debug_repository()` hardcodes 21 items as fallback; should be removed once real data loading is complete

### Magic Core Shop
- **Hardcoded exchange rates** — `magic_core_shop_scene.py:16` `MC_SIZES` list with hardcoded GP-per-unit rates; should load from scenario YAML
- **Hardcoded MC labels/order** — `item_logic.py:14` `MC_IDS`, `MC_ORDER`, `MC_LABELS` are hardcoded; should derive from item data

## Feature
- Party join flow | Full party
- Shop + Apothecary | Buy/craft
- Boss encounters + story act transitions | Story progression
- Full playthrough pass | End-to-end
