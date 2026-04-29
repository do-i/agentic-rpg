# Code Review Plan

Date: 2026-04-27
Scope: `engine/` and `tests/` (199 source files, 14,742 LOC engine; 64 test files, 9,224 LOC tests, 892 tests).
Method: Read-only review focused on five axes: bugs, performance, duplication, breaking up oversized modules, and test gaps.

Severity tags:
- **P1** — broken / data loss / incorrect game behavior. Fix before next release.
- **P2** — wrong-but-benign or fragile. Schedule.
- **P3** — code smell / style / minor inefficiency.

---

## 1. Bugs

### 1.7 [P2] ~~`Combatant.tick_end_of_turn` mutates list while iterating effects~~ — DONE 2026-04-27
File: `engine/battle/combatant.py:153-167`

Combined the duration decrement and filter pass into a single loop that builds a `remaining` list — no more reading from `self.status_effects` while a replacement is being constructed.

---

## 2. Performance

### 2.2 [P2] ~~YAML re-loaded on every dialogue interaction~~ — DONE 2026-04-27
File: `engine/dialogue/dialogue_engine.py:47-74`

Added `load_yaml_required_cached`, `load_yaml_optional_cached`, and `clear_yaml_cache` to `engine/io/yaml_loader.py`. `DialogueEngine.resolve()` now uses `load_yaml_optional_cached` and `spell_logic._load_class_abilities` uses `load_yaml_required_cached`. Cache is keyed on the resolved Path so different tmp_paths don't collide between tests; missing files are also cached so we don't re-stat. Test count 1072 → 1078 (6 new tests in `test_yaml_loader.py` covering first-call read, second-call cache hit, clear_yaml_cache invalidation, and the missing-file caching behavior).

### 2.3 [P2] ~~Map YAML opened twice during scene init~~ — DONE 2026-04-27
File: `engine/world/world_map_scene.py:177-196`

Added `parse_from_map_data(data)` to `NpcLoader` and `ItemBoxLoader` that take an already-parsed dict. `world_map_init.py` now reads the map YAML once via `load_yaml_optional` and passes the parsed dict to both loaders plus the BGM and spawn-config blocks. The original `load_from_map(path)` methods stay as thin wrappers so existing call sites and tests are unchanged. Test count 1078 → 1086 (8 new tests in `test_npc_loader.py` and `test_item_box_loader.py` for the no-disk-IO path).

### 2.6 [P2] ~~WorldMapScene rebuilds visibility lists redundantly~~ — DONE 2026-04-27
File: `engine/world/world_map_scene.py:600-651`

Added `_refresh_visibility()` which rebuilds `_visible_npcs`, `_visible_boxes`, and their collision-rect lists from current `FlagState`. `update()` calls it once per tick at the top; `render()` falls back to it only if it ran first (e.g. an overlay is active and update short-circuited). The per-NPC `other_rects` is now a slice around the current index instead of an O(N²) "filter by identity" comprehension.

### 2.7 [P2] ~~`EnemySpawner.update` rebuilds rect lists per frame O(n²)~~ — DONE 2026-04-27
File: `engine/encounter/enemy_spawner.py:122-127`

Replaced the per-enemy zip-and-filter comprehension with `all_rects[:i] + all_rects[i+1:]`. Linear in N rather than the implicit N² scan, no `is` identity check on every iteration.

### 2.8 [P3] ~~`EnemyLoader` and `EnemySpawner` re-load sprite sheets across maps~~ — DONE 2026-04-28

Added `engine/world/sprite_sheet_cache.py` — a process-wide `SpriteSheetCache` keyed by absolute `Path`. `get()` returns the cached `SpriteSheet`, loading on first call; missing files and load failures are also cached as `None` so we don't re-stat or retry the parse. `AppModule.provide_sprite_sheet_cache` registers it as a singleton. `NpcLoader`, `EnemySpawner`, and the protagonist sprite path in `world_map_init._load_protagonist_sprite` all route through the same cache, threaded via `SceneDeps.sprite_cache` → `WorldMapScene` → `init_world_map` → `_build_spawner`. Sheets now survive map transitions instead of being re-read whenever the spawner is rebuilt or `parse_from_map_data` runs. Test count 1219 → 1224 (5 new tests in `test_sprite_sheet_cache.py` covering cache hit, missing-path caching, load-failure caching, and `clear()`).

### 2.9 [P3] Autosave on every portal transition
File: `engine/world/world_map_logic.py:145`

`game_state_manager.save(state, slot_index=0)` writes a full YAML save on every portal traversal. With many small maps, this hits disk constantly. Acceptable for an SSD, but consider debouncing or only autosaving on entering "checkpoint" maps.

---

## 3. Duplication

### 3.2 [P2] Sprite-init pattern duplicated across overlays

`item_shop_scene.py:56-62`, `apothecary_scene.py:61-67`, `inn_scene.py:80-86` all have the identical `_init_sprite` body. Extract to `engine/world/sprite_sheet.py` as `SpriteSheet.load_npc_face(path, size) -> Surface | None`.

### 3.3 [P2] ~~`_weighted_pick` reimplemented twice~~ — DONE 2026-04-27

Added `engine/util/weighted_pick.py` with a generic `weighted_pick(rng, entries, weight_fn) -> entry | None`. Both call sites now use it: `EncounterResolver.pick_formation` passes `lambda e: e.weight` over Formations and the loot path in `RewardCalculator.calculate_loot` passes `lambda e: e.get("weight", 1)` over pool dicts then reads `entry.get("item")`. The local `_weighted_pick` helper in `battle_rewards.py` and the bound method on `EncounterResolver` are gone. The old `TestWeightedPick` in `test_battle_rewards.py` and the bound-method tests in `test_encounter_resolver.py` were rehomed as `tests/unit/core/state/test_weighted_pick.py` (7 tests covering the util directly) and a `TestPickFormationWeighted` class that exercises the public `pick_formation` API end-to-end. Test count 1086 → 1090.

### 3.6 [P3] `_clamp_scroll` re-implemented per shop scene

`item_shop_scene.py:178-181` and `apothecary_scene.py:212-215` both do:
```python
self._scroll = ItemSelectionView.clamp_scroll(
    self._list_sel, self._scroll, len(items), VISIBLE_ROWS,
)
```
Different list source, same body. Could inline; just noting for context.

### 3.7 [P3] `MapState.from_dict` uses `.get(k, fallback)` violating CLAUDE.md feedback memory

File: `engine/common/map_state.py:56-60` — uses `.get("position", [0,0])`, `.get("current", "")`, `.get("visited", [])`. Violates the "no hardcoded defaults" feedback memory. Same in `dialogue_engine.py`, `item_catalog.py`, `item_effect_handler.py`, etc. (See §1.4 for the pattern.) Audit all `data.get(k, default)` callsites and convert to explicit raises with file/property/example.

---

## 4. Break up oversized modules

### 4.2 [P1] `engine/battle/battle_scene.py` (451 lines)

Mixes input handling for 6 phases, sub-menu construction, and result handling. Extract:
- `engine/battle/battle_input.py` — `_handle_cmd`, `_handle_sub`, `_handle_target` and their selection-tracking state.
- `engine/battle/battle_menu_builder.py` — `_open_spell_menu`, `_open_item_menu` (currently builds dicts with hardcoded `TARGET_MAP`).
- The 451-line scene becomes pure orchestration.

### 4.3 [P2] ~~`engine/battle/battle_renderer.py` (416 lines)~~ — DONE 2026-04-27

Split the 453-line renderer into one orchestrator + four panel classes + a shared HitFlash helper:
- `engine/battle/battle_enemy_area_renderer.py` — `EnemyAreaRenderer` owns the floor strip, enemy sprite/HP-bar drawing, and the KO ghost cache (which used to live on BattleRenderer).
- `engine/battle/battle_party_panel_renderer.py` — `PartyPanelRenderer` draws the per-member roster row.
- `engine/battle/battle_command_panel_renderer.py` — `CommandPanelRenderer` covers the turn header, main command list, sub-menu, and target-select prompt.
- `engine/battle/battle_damage_float_renderer.py` — `DamageFloatRenderer` owns the per-DamageFloat shadow/foreground cache.
- `engine/battle/battle_hit_flash.py` — shared `HitFlash` helper owns the per-(w,h) flash overlay cache; both the enemy area and party panel use the same instance so they share the cache.

`BattleRenderer.render()` is now a ~15-line composition: paint background, dispatch to enemy area, draw dividers + party panel + command panel + message line, then damage floats. The 4-line message panel stayed inline since it isn't worth its own class.

Test count unchanged (1090 → 1090): the existing `test_battle_renderer_caches.py` was rewritten to reach into the new panel-renderer fields (`renderer._damage_floats._cache`, `renderer._enemy_area._ko_cache`, `renderer._hit_flash._flash_cache`) so all 11 cache assertions still hold.

### 4.4 [P2] ~~`engine/equipment/equip_scene.py` (395 lines) and `engine/spell/spell_scene.py` (355 lines)~~ — DONE 2026-04-28

Added `engine/common/wizard_scene.py` with a `WizardScene` base + `WizardPage` dataclass. Pages declare `count_fn`, `on_confirm` (returns next page id or None), `on_back` (returns previous page id or None to close the scene), and own their own `selection`. The base owns: SFX `_play(key)`, hover-beep `_set_sel`, the per-page UP/DOWN clamp, ENTER/ESC/M routing, the scene-close path, and a `_is_input_blocked` / `_handle_blocked_input` hook for modal overlays. `EquipScene` registers MEMBER/SLOT/PICKER pages and supplies the unique render code; `SpellScene` registers MEMBER/SPELL pages and uses the modal hook to gate input while the target overlay or popup is active. equip_scene 380 → 326 lines, spell_scene 334 → 287 lines; remaining bulk is the genuinely-unique render code per scene. Test count 1090 → 1107 (17 new tests in `test_wizard_scene.py` covering page registration, selection clamping, hover SFX, ENTER/ESC navigation, the empty-page no-op, the modal-overlay hooks, and `set_return_scene`). All existing equip/spell scene tests were updated to read selection state via `scene.page_id` and `scene._page(name).selection`.

### 4.5 [P2] ~~`engine/battle/battle_logic.py` (343 lines)~~ — DONE 2026-04-28

Pulled action resolution and turn-advance helpers out of battle_logic into their own modules:
- `engine/battle/battle_floats.py` (42 lines) — float colors and the `float_pos` / `enemy_rect_size` helpers, broken out so `action_resolver` and `turn_advance` can both depend on them without battle_logic importing back into them (which would loop).
- `engine/battle/action_resolver.py` (226 lines) — `resolve_action`, `roll_and_apply_side_effects`, `SIDE_EFFECT_KINDS`, plus internal `_resolve_attack` / `_resolve_spell` / `_resolve_item` per-target functions. The 100-line `for target in targets` switch is now three short single-purpose functions; `resolve_action` itself is the dispatcher (defend short-circuit, MP-deduct-up-front gate, post-loop item qty decrement).
- `engine/battle/turn_advance.py` (58 lines) — `tick_active_end_of_turn`, `advance_to_next_turn`, `skip_if_incapacitated`.
- `engine/battle/battle_logic.py` (134 lines) — keeps `handle_victory`, `handle_defeat`, `sync_party_state`, `check_result`, `attempt_flee`, the FLEE constants, and a re-export shim so existing imports (`battle_scene`, `battle_enemy_logic`, `test_battle_logic`) keep working unchanged. 348 → 134 lines. Test count unchanged at 1107 — no behavior change, no new helpers worth their own test file (the existing `test_battle_logic.py` already covers all three relocated areas).

### 4.7 [P3] `engine/status/status_renderer.py` (329 lines), `engine/item/item_renderer.py` (318 lines), `engine/encounter/enemy_sprite.py` (307 lines), `engine/shop/apothecary_renderer.py` (305 lines), `engine/world/npc.py` (303 lines)

All under 350 lines and reasonably cohesive. Tag for later if they grow further.

---

## 5. Test coverage gaps

Current state: 64 test files, 892 tests. 64 engine modules have no matching `test_*.py` (matched by basename). Highlights:

### 5.1 [P1] Untested critical infra
- `engine/io/save_manager.py` — `GameStateManager.save/load/list_slots/_slot_from_file/_serialize`. There is `tests/unit/core/state/test_game_state_manager.py` but the module name doesn't match — confirm what it actually covers; checksum round-trip and corrupted-file handling deserve explicit tests.
- `engine/world/tile_map.py` — `_load_enemy_spawn_tiles`, `_load_boss_spawn_tile`, `TileMap.render` viewport culling math.
- `engine/io/manifest_loader.py` — no test file by name.
- `engine/io/game_state_loader.py` — no test file by name.

### 5.2 [P1] Untested battle UI logic
- `engine/battle/battle_scene.py` — no test for `_handle_target`/`_handle_sub` (the spell/item menu wiring that has the dataclass-equality bug in §1.1).
- `engine/battle/battle_state.py` — `build_turn_order` tie-breaking, `advance_turn` skip-dead behavior, `update_floats` purge.
- `engine/battle/battle_enemy_logic.py` — no test file. AI resolution is the hardest thing to test by hand.
- `engine/battle/post_battle_scene.py`, `engine/battle/game_over_scene.py` — no tests.

### 5.3 [P2] ~~Untested world systems~~ — DONE 2026-04-28
- `engine/world/tile_map_factory.py` — covered by `tests/unit/world/test_tile_map_factory.py` (2 tests: create returns a TileMap loaded via `pytmx.load_pygame`; the factory is stateless across multiple maps).
- `engine/encounter/encounter_zone_loader.py` — covered by `tests/unit/core/encounter/test_encounter_zone_loader.py` (15 tests: required-field validation, entry/boss/barrier round trips, zone_id stem fallback, optional metadata).
- `engine/encounter/encounter_zone_data.py` — covered by `tests/unit/core/encounter/test_encounter_zone_data.py` (10 tests: dataclass defaults, frozen-ness, EncounterSet.total_weight).
- `engine/world/tile_map.py` is now well-covered (added in step 8). `engine/world/world_map_scene.py` integration tests left out of scope — the plan tagged this as "no integration test exists" but the scene was refactored in step 5 into much smaller helpers (each tested individually); a full integration test is a separate effort beyond §5.3's "by basename" coverage gap. Test count 1107 → 1134.

### 5.4 [P2] ~~Untested rendering primitives (acceptable but call out)~~ — DONE 2026-04-28

Added `tests/unit/core/battle/test_battle_renderer_layout.py` with 16 tests covering the pure-helper surface called out in §5.4: `BattleRenderer` layout math (bottom_h, party_w = 25%, cmd_w = 30%, msg_x sum, msg_w fills remainder), `enemy_rect_size` (boss → large; non-boss table indexed by `len(name) % 3`), `float_pos` (party float anchored by row spacing, enemy floats use layout offsets, boss floats lift higher than normal sprites), and the `HP_LOW_THRESHOLD` branch logic (value pinned at 0.35; the renderer uses `<=` so at-threshold counts as low; 0.0 low, 1.0 OK). The damage-float / KO-ghost / hit-flash caches were already covered in `test_battle_renderer_caches.py`. Test count 1134 → 1150.

### 5.5 [P2] ~~Untested IO/state~~ — DONE 2026-04-28
- `engine/party/member_state.py` — `tests/unit/core/state/test_member_state.py` (10 tests: construction, unloaded stat_growth defaults, `load_class_data` round-trip, missing-stat KeyError, equipment_slots None-list normalization, the legacy `load_stat_growth` alias, and the protagonist marker in repr).
- `engine/item/item_entry_state.py` — `tests/unit/core/state/test_item_entry_state.py` (8 tests: minimum construction, default name title-casing, underscore handling, independent default tags set, explicit tags/qty/locked, repr).
- `engine/item/item_defs_data.py` — `tests/unit/core/state/test_item_defs_data.py` (9 tests: FieldItemDef defaults, frozen-ness, independent default `cures`/`messages` lists, revive_hp_pct, key-item non-consumable, UseResult success/warning/messages).
- `engine/audio/bgm_manager.py` — `tests/unit/core/state/test_bgm_manager.py` (11 tests: index parsing with category.key keys, non-dict category skip, enabled gate on `play`/`play_key`/`stop`, repeat-call no-op, unknown-key silence).
- `engine/audio/sfx_manager.py` — `tests/unit/core/state/test_sfx_manager.py` (15 tests: index parsing flatness, missing-file skip, enabled gate, plus the entire `play_battle_action` dispatcher across attack/defend/heal/revive/buff(by stat)/element/item/unknown).
- `engine/common/save_slot_data.py` was already covered by `tests/unit/core/models/test_save_slot.py`.

Test count 1150 → 1203.

### 5.6 [P2] ~~Branch coverage gaps in tested modules~~ — DONE 2026-04-28
- `roll_and_apply_side_effects` is well-covered by the existing `TestRollAndApplySideEffects` (6 cases: applied/skipped by chance, knockback atk_modifier, KO early-return guard, unknown-effect ignore, multi-effect independent rolls).
- The spell `revive_hp_pct` branch had a test for the KO target but not for an alive target — the no-op path could silently change. Added `test_revive_spell_on_alive_target_is_no_op` (HP unchanged, MP still spent up front, no message). Also added `test_heal_spell_skips_ko_target_without_revive_pct` to pin that plain Heal short-circuits on KO targets via `Combatant.apply_heal`.
- `_weighted_pick` was unified in §3.3 and has 7 dedicated tests in `tests/unit/core/state/test_weighted_pick.py` plus the `test_distribution_unbiased_for_equal_weights` regression in `test_encounter_resolver.py` that catches the original §1.2 truncation bias.
- `RepositoryState` cap behavior is well-covered: `test_add_gp_capped_at_max`, `test_add_gp_exact_cap`, `test_add_item_qty_capped`, `test_add_item_new_entry_capped`, `test_add_item_logs_warning_when_clipped`. §1.5 was already addressed in step 1.

Test count 1203 → 1205 (+2).

### 5.7 [P3] Test directory consolidation
`tests/unit/core/` and `tests/unit/world/` split is already noted in CLAUDE.md ("legacy path"). Plan a rename pass once the bug fixes above land.

---

## 6. Suggested execution order

1. ~~**Extract menu/list shared code (3.1)**~~ — **DONE 2026-04-27**. Promoted `C_SEL`/`C_ROW_SEL`/`C_HEAD` into `engine/common/color_constants.py`, added `engine/common/menu_row_renderer.py` with the shared `render_row()` body that `equip_scene` and `spell_scene` were duplicating, added `engine/common/menu_popup.py` for the centered "ENTER/ESC to dismiss" popup used by `spell_scene` (apothecary/inn/item_shop draw their own modal frames so they were left alone), and added `SpriteSheet.load_npc_face(path, size)` to centralize the inn/item_shop/apothecary `_init_sprite` body. Test count 949 → 960 (11 new tests across `test_menu_row_renderer.py`, `test_menu_popup.py`, `test_sprite_sheet.py::TestLoadNpcFace`). The full WizardScene base + popup overlay class noted in §3.1 is left for §4.4 (P2).
2. ~~**Break up `battle_scene` and `battle_renderer` (4.2, 4.3)**~~ — **DONE 2026-04-27**. See §4.2 (battle_scene → input controller + menu builder) and §4.3 (battle_renderer → orchestrator + 4 panel classes + HitFlash helper).
3. ~~**Test gaps (§5)**~~ — **DONE 2026-04-28**. §5.1 (critical infra), §5.2 (battle UI), §5.3 (world systems), §5.4 (renderer layout), §5.5 (IO/state DTO + audio), §5.6 (branch coverage gaps) — all completed. Test count 949 → 1206.
4. ~~**Step 4 — P3 bug cleanups (§1.9–§1.12)**~~ — **DONE 2026-04-28**. WorldMapScene lazy-init lifted out of render fast path via `_ensure_init`; ESC during target/sub-menu now clears `pending_action` (controller + scene + regression test); `_meta_ts_to_display` uses `strptime`/`strftime`; every bare `except Exception` in the engine has been narrowed and now logs through `logging.warning`. Test count 1205 → 1206 (+1 regression test for the ESC pending_action clear).

---

## 7. Out of scope (noted, not pursued)

- The `.get(k, default)` audit (§3.7) is a project-wide policy enforcement task that touches dozens of files; recommend a separate ticket.
- Test directory reorganization (§5.7) — already on the team's radar per CLAUDE.md.
- The 5 ~300-line files in §4.7 — under threshold; revisit when they cross 400.
