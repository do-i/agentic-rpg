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

### 1.9 [P3] `WorldMapScene.update` may run before `render` initializes the map
File: `engine/world/world_map_scene.py:550-642`

`_init()` is called lazily in `render()`. The first frame's `update()` runs before `render()` and short-circuits on `if self._player is None`. This works, but lazy init from render is unusual. Move init into `enter()`/`activate()` if the scene base supports lifecycle hooks, or call `_init()` from `reset()`.

### 1.10 [P3] `_handle_target` ESC leaves `pending_action` populated
File: `engine/battle/battle_scene.py:310-317`

ESC during target select returns to `PLAYER_TURN` and clears `_sub_items`, but leaves `state.pending_action` set. The next confirm overwrites it, so no observable bug, but `pending_action` should be cleared when the action is abandoned.

### 1.11 [P3] `_meta_ts_to_display` fragile parser
File: `engine/io/save_manager.py:31-35`

Hand-rolled string surgery on a known format (`YYYY-MM-DD-HH-MM-SS`). If the format ever changes, this silently produces nonsense. Use `datetime.strptime` and re-`strftime`.

### 1.12 [P3] Bare `except Exception` swallows sprite/asset load failures silently
Files (14 sites): `inn_scene.py:85`, `item_shop_scene.py:61`, `apothecary_scene.py:66`, `enemy_spawner.py:220`, `sfx_manager.py:44`, `battle_asset_cache.py:60,91,105`, `save_manager.py:140`, `world_map_scene.py:244`, `item_box_loader.py:41`, `status_renderer.py:82`, `enemy_loader.py:102`, `npc_loader.py:80`.

The pattern is "fail back to placeholder," but several sites just `pass` with no log line, which makes asset issues invisible in playtesting. Standardize on `except (FileNotFoundError, pygame.error) as e: logging.warning(...)` with a concrete narrowed exception list per site.

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

### 2.7 [P2] `EnemySpawner.update` rebuilds rect lists per frame O(n²)
File: `engine/encounter/enemy_spawner.py:122-127`

```python
active = [e for e in self._all_enemies if e.active]
all_rects = [e.collision_rect for e in active]
for enemy in active:
    other_rects = [r for e, r in zip(active, all_rects) if e is not enemy]
```

For typical N≤8 active enemies this is fine, but the inner zip-comprehension allocates. Cleaner: pass `all_rects` and the enemy's own index, or use a flat list and have each enemy ignore self by `is` check.

### 2.8 [P3] `EnemyLoader` and `EnemySpawner` re-load sprite sheets across maps
The spawner has a per-instance `_sprite_cache`, but the spawner is recreated on every map transition (`world_map_scene.py:546`), so sprites are reloaded on every map change. Promote sprite caching to a singleton (`SpriteSheetCache`) injected via `AppModule`.

### 2.9 [P3] Autosave on every portal transition
File: `engine/world/world_map_logic.py:145`

`game_state_manager.save(state, slot_index=0)` writes a full YAML save on every portal traversal. With many small maps, this hits disk constantly. Acceptable for an SSD, but consider debouncing or only autosaving on entering "checkpoint" maps.

---

## 3. Duplication

### 3.1 [P1] Field/menu scenes share a near-identical "list/picker with hover SFX" pattern

The same idiom appears in:
- `engine/equipment/equip_scene.py` — `_set_member_sel`, `_set_slot_sel`, `_set_item_sel`, `_play`, `_render_row`, `_init_fonts`.
- `engine/spell/spell_scene.py` — `_set_member_sel`, `_set_spell_sel`, `_play`, `_render_row`, `_init_fonts`, `_render_popup`.
- `engine/shop/item_shop_scene.py` — `_handle_list`, `_handle_qty` (hover/confirm/cancel SFX).
- `engine/shop/apothecary_scene.py` — `_handle_list`, `_handle_detail`.
- `engine/inn/inn_scene.py` — confirm/cancel pattern.
- `engine/field_menu/field_menu_scene.py` — same.

Common pieces to extract:
1. `MenuScene` base or mixin: `_play_sfx(key)`, `_set_sel(field, new_value)` with hover beep, the standard `popup_active`/`popup_text` flow.
2. `MenuRowRenderer` helper: `_render_row(screen, x, y, w, text, focused, dimmed_sel, color)` — `equip_scene._render_row` and `spell_scene._render_row` are character-identical. Move to `engine/common/menu_row_renderer.py`.
3. `Popup` overlay: `inn`, `spell`, `item_shop`, `apothecary` each open and dismiss a single-line popup with ENTER/ESC. Make a `Popup(text, on_dismiss)` overlay class.
4. Stat/font color constants: `C_SEL`, `C_ROW_SEL`, `C_HEAD` are redefined in `equip_scene` and `spell_scene`. Move to `engine/common/color_constants.py`.

### 3.2 [P2] Sprite-init pattern duplicated across overlays

`item_shop_scene.py:56-62`, `apothecary_scene.py:61-67`, `inn_scene.py:80-86` all have the identical `_init_sprite` body. Extract to `engine/world/sprite_sheet.py` as `SpriteSheet.load_npc_face(path, size) -> Surface | None`.

### 3.3 [P2] `_weighted_pick` reimplemented twice

- `engine/encounter/encounter_resolver.py:33-43` — manual cumulative (and biased per §1.2).
- `engine/battle/battle_rewards.py:201-207` — uses `rng.choices`.

Promote a single `engine.util.weighted_pick(rng, entries, weight_fn)` and call it from both.

### 3.5 [P3] `(if self._sfx_manager: self._sfx_manager.play(key))` pattern repeats ~80 times

Most files guard `_sfx_manager` for truthiness. Either:
- Make `SfxManager` always non-None (use a `NullSfxManager` placeholder), or
- Add a tiny `_sfx(self, key)` helper to a shared base.

The `equip_scene._play` / `spell_scene._play` already do this and would be the model.

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

### 4.3 [P2] `engine/battle/battle_renderer.py` (416 lines)

Already split asset loading to `BattleAssetCache`. Now split the renderer further by "panel":
- `EnemyAreaRenderer` (`_draw_enemy_area`, `_draw_enemy`).
- `PartyPanelRenderer` (`_draw_party_panel`, `_draw_party_row`).
- `CommandPanelRenderer` (`_draw_command_panel`, `_draw_main_cmd`, `_draw_submenu`).
- `MessagePanelRenderer` + `DamageFloatRenderer`.

`BattleRenderer.render` becomes a 10-line composition.

### 4.4 [P2] `engine/equipment/equip_scene.py` (395 lines) and `engine/spell/spell_scene.py` (355 lines)

Both are MEMBER → SLOT/SPELL → DETAIL three-page wizards with near-identical structure (see §3.1). Extract a `WizardScene` base class with a list of `WizardPage` objects so both scenes shrink to ~120 lines plus their unique data.

### 4.5 [P2] `engine/battle/battle_logic.py` (343 lines)

Already split spell side-effects, EXP, flee, and turn ticks. Push further:
- `engine/battle/action_resolver.py` — `resolve_action` (the 100-line `for target in targets` switch on `atype`). Replace the if/elif chain with one resolver per action type (`AttackResolver`, `SpellResolver`, `ItemResolver`).
- `engine/battle/turn_advance.py` — `tick_active_end_of_turn`, `advance_to_next_turn`, `skip_if_incapacitated`.

### 4.6 [P3] `engine/app_module.py` (322 lines)

The DI module is fine in shape but the `provide_scene_registry` provider is 90 lines of factory bodies. Split:
- `engine/scenes/scene_registrar.py` — pure function `register_scenes(registry, deps)` that takes everything and registers. Keeps `AppModule` to wiring `@provider` methods only.

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

### 5.3 [P2] Untested world systems
- `engine/world/world_map_scene.py` — no integration test exists (only `test_world_map_logic.py` for the extracted helpers and `test_world_map_item_box_integration.py` for chests).
- `engine/world/tile_map_factory.py` — no tests.
- `engine/world/portal_loader.py` is tested; `engine/world/tile_map.py` is not.
- `engine/encounter/encounter_zone_loader.py`, `engine/encounter/encounter_zone.py`, `engine/encounter/encounter_zone_data.py` — no tests.

### 5.4 [P2] Untested rendering primitives (acceptable but call out)
- All `*_renderer.py` files (battle/world/item/status/shop/apothecary/menu) lack tests — pure pygame drawing is hard to unit-test, but at minimum exercise their pure helpers (e.g., `BattleRenderer.bottom_h`/`party_w`/`cmd_w` math, color choices via `HP_LOW_THRESHOLD`).

### 5.5 [P2] Untested IO/state
- `engine/party/member_state.py`, `engine/item/item_entry_state.py`, `engine/item/item_defs_data.py`, `engine/common/save_slot_data.py` — DTOs with custom logic / serialization shouldn't be assumed correct.
- `engine/audio/bgm_manager.py`, `engine/audio/sfx_manager.py` — at minimum smoke-test the YAML index parse path.

### 5.6 [P2] Branch coverage gaps in tested modules
- `engine/battle/battle_logic.py` has `test_battle_logic.py` but `roll_and_apply_side_effects` (line 29) and the spell `revive_hp_pct` branch (line 134) need explicit cases; both are easy to break under refactor.
- `engine/encounter/encounter_resolver.py` — `_weighted_pick` (the buggy one) has no direct test; the bias from §1.2 would be caught by a test that pumps roll=100 a few times.
- `engine/party/repository_state.py` — confirm there's a test asserting the cap behavior in §1.5; if not, add one that documents *and* fails on silent loss when this is fixed.

### 5.7 [P3] Test directory consolidation
`tests/unit/core/` and `tests/unit/world/` split is already noted in CLAUDE.md ("legacy path"). Plan a rename pass once the bug fixes above land.

---

## 6. Suggested execution order

1. ~~**Extract menu/list shared code (3.1)**~~ — **DONE 2026-04-27**. Promoted `C_SEL`/`C_ROW_SEL`/`C_HEAD` into `engine/common/color_constants.py`, added `engine/common/menu_row_renderer.py` with the shared `render_row()` body that `equip_scene` and `spell_scene` were duplicating, added `engine/common/menu_popup.py` for the centered "ENTER/ESC to dismiss" popup used by `spell_scene` (apothecary/inn/item_shop draw their own modal frames so they were left alone), and added `SpriteSheet.load_npc_face(path, size)` to centralize the inn/item_shop/apothecary `_init_sprite` body. Test count 949 → 960 (11 new tests across `test_menu_row_renderer.py`, `test_menu_popup.py`, `test_sprite_sheet.py::TestLoadNpcFace`). The full WizardScene base + popup overlay class noted in §3.1 is left for §4.4 (P2).
2. **Break up `battle_scene` and `battle_renderer` (4.2, 4.3)** — independent of #1.
   - ~~**§4.2 battle_scene split**~~ — **DONE 2026-04-27**. Pulled the player-side input layer into `engine/battle/battle_input.py` (`BattleInputController` owns cmd/sub/target selection state, hover/confirm/cancel SFX, and the per-phase `handle_cmd`/`handle_sub`/`handle_target` methods plus the `_confirm_cmd`/`_confirm_sub` dispatchers; the scene supplies a `BattleInputCallbacks` for do_resolve / open_spell_menu / open_item_menu / attempt_run / enter_resolve). Pulled the spell/item sub-menu construction (and the field→battle `TARGET_MAP`) into `engine/battle/battle_menu_builder.py` as pure builders. `battle_scene.py` shrank 451 → 277 lines and now only orchestrates resolution, turn ticks, and BGM/SFX gating. Test count 960 → 1004 (44 new tests in `test_battle_menu_builder.py` and `test_battle_input.py`, covering nav, clamping, hover/confirm SFX, silenced/disabled cases, every target_type branch, and the lifecycle helpers).
   - **§4.3 battle_renderer split** — pending.
3. **Test gaps (§5)** — driven alongside each refactor; do not ship #2 without its corresponding test additions.
   - ~~**§5.1 critical infra**~~ — **DONE 2026-04-27**. Added 6 tests in `test_manifest_loader.py` (parsed-dict round-trip, missing-file FileNotFoundError, empty/garbled YAML, scenario_path property), 9 tests in `test_tile_map.py` for `_load_enemy_spawn_tiles` (gid filtering, missing layer, type-mismatched layer with same name) and `_load_boss_spawn_tile` (tile-grid snapping, first-object-only, type guards), and 6 tests in `test_game_state_manager.py` for checksum round-trip + tamper detection, truncated-file slot fallback, and `_meta_ts_to_display` format conversion. `engine/io/game_state_loader.py` already had `test_game_state_loader.py`. Test count 1004 → 1025.
   - ~~**§5.2 battle UI**~~ — **DONE 2026-04-27**. `_handle_target`/`_handle_sub`/`_handle_cmd` were covered when extracted to `battle_input.py` in step 7. Added 16 tests in `test_battle_state.py` for `build_turn_order` (DEX desc + party-wins-tie + dead-excluded + active_index reset), `advance_turn` (skip-dead + wrap + turn_count + termination), `update_floats` (purge expired + advance position), and the alive_party/ko_party/alive_enemies/party_wiped/enemies_wiped helpers. Added 13 tests in `test_post_battle_scene.py` for the EXP-fill animation, the skip-on-first-press / continue-on-second-press flow across SPACE/ENTER/Z, and render smoke for empty/level-up/loot/KO cases. Added 18 tests in `test_game_over_scene.py` for initial selection (skips disabled "Load Game" when no saves), nav clamping, hover SFX, confirm dispatch (load → load_game scene, title → title scene, quit → posts QUIT, no-op when Load Game disabled), fade animation, and render smoke. `battle_enemy_logic.py` already has wide coverage in `tests/unit/core/scenes/test_battle_logic.py` (`TestPickEnemyAction`, `TestResolveTargeting`, `TestCheckCondition`, `TestResolveEnemyTurnWithAI`). Test count 1025 → 1072.

---

## 7. Out of scope (noted, not pursued)

- The `.get(k, default)` audit (§3.7) is a project-wide policy enforcement task that touches dozens of files; recommend a separate ticket.
- Test directory reorganization (§5.7) — already on the team's radar per CLAUDE.md.
- The 5 ~300-line files in §4.7 — under threshold; revisit when they cross 400.
