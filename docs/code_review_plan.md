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

### 1.1 [P1] Spell MP deducted via `==` on dataclass causes incorrect MP cost on multi-target spells
File: `engine/battle/battle_logic.py:131`

```python
if source and target == targets[0]:
    source.mp = max(0, source.mp - ab["mp_cost"])
```

`Combatant` is a `@dataclass` with default `eq=True`, so `==` compares all fields, not identity. The intent is "deduct MP only on the first iteration of the multi-target loop." Two enemies of the same type with identical fresh stats compare equal until one of them has mutated. In practice this happens to work for damaging spells (the first target's HP changes after `apply_damage`, breaking equality), but for **buff/debuff/utility AOEs that don't mutate the target's compared fields**, every iteration sees `target == targets[0] == True` (identical buff state) and MP is deducted only once correctly — UNLESS the spell mutates `status_effects`, which is also part of `__eq__`. Outcome is non-obvious and depends on the spell type and ordering.

**Fix:** use `target is targets[0]`, or pull the MP deduction out of the per-target loop.

### 1.2 [P2] `EncounterResolver._weighted_pick` uses biased integer math
File: `engine/encounter/encounter_resolver.py:33-43`

`int(entry.weight * 100 / total)` truncates per entry, so for weights `[1,1,1]` the cumulative caps at 99 and `roll == 100` falls through to `entries[-1]`, biasing the last entry. `RewardCalculator._weighted_pick` already uses `rng.choices` correctly — replace the encounter version with the same approach.

### 1.3 [P2] `apply_transition` autosaves with old map but new position-target pairing
File: `engine/world/world_map_logic.py:138-148`

```python
state.map.set_position(player.tile_position)
game_state_manager.save(state, slot_index=0)
new_map = transition.get("map", state.map.current)
state.map.move_to(new_map, Position.from_list(transition["position"]))
```

Order: position is set to the player's current pixel-tile, then autosaved (fine), then moved. If a save is loaded between the save call and the move call (e.g., a crash mid-transition), the player wakes up at the **old map** at the **portal trigger tile**, which is at the edge of the map. Cosmetic but reproducible. Move the autosave to after `move_to`.

### 1.4 [P2] `transition.get("map", state.map.current)` silently allows portals without a target map
File: `engine/world/world_map_logic.py:147`

A misconfigured portal that omits `map` will quietly wrap the player back to the same map at the new position. CLAUDE.md feedback memory explicitly forbids `.get(k, default)`; should `raise KeyError` like the sibling `position` check on line 142.

### 1.5 [P2] `RepositoryState.add_item` silently caps qty
File: `engine/party/repository_state.py:83-101`

```python
self._items[item_id].qty = min(self._items[item_id].qty + qty, self._item_qty_cap)
```

If the caller asks to add 10 but only 3 fit, the caller has no way to know. Loot drops, item-box pickups, and shop purchases all assume the requested qty was added. Consider returning the actual delta, or raising/warning when the cap clips. Same applies to `add_gp`.

### 1.6 [P2] `apply_damage` order-of-operations: `actual` is computed against pre-decrement HP but with post-defending amount
File: `engine/battle/combatant.py:105-117`

```python
actual = min(amount, self.hp)
self.hp = max(0, self.hp - amount)
```

Functionally correct (actual is "displayed damage" capped at HP). But the `max(0, …)` guard is redundant since `min(amount, self.hp)` already ensures `self.hp - amount >= 0` once `amount` is clamped — except `self.hp -= amount` uses the unclamped `amount`, so the `max(0,…)` matters. Subtle. Not a bug, but a comment-worthy invariant.

### 1.7 [P2] `Combatant.tick_end_of_turn` mutates list while iterating effects
File: `engine/battle/combatant.py:153-167`

The two passes (DOT scan, then duration decrement, then filter) are correct, but the `for s in self.status_effects: s.duration_turns -= 1` followed by `self.status_effects = [...]` mutates the list reference. Safe in Python but fragile if a future hook adds during iteration.

### 1.8 [P3] `_apply_to_member` called from outside its class
File: `engine/battle/battle_logic.py:173`

```python
effect_handler._apply_to_member(defn, target)
```

`_apply_to_member` is private but battle_logic reaches across classes to invoke it. Promote to a public method (`apply_to_combatant` or `apply_one`) and route the public `apply()` through it.

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

### 2.1 [P1] Tile rendering does per-tile `get_tile_image` lookup every frame
File: `engine/world/tile_map.py:106-112`

For a typical 1280×766 viewport at 32-px tiles with 3 visible layers: `40×24×3 = 2880` tile lookups per frame at 60 fps = **172,800 lookups/sec**. `pytmx.get_tile_image` is well known to be slow for this pattern.

**Fix options:**
1. Pre-render each layer to a single offscreen `Surface` once at map load, then `screen.blit(layer_surf, (-offset_x, -offset_y))` per frame. Memory cost: `width_px × height_px × 4 bytes × num_layers` (a 50×50 map = ~30 MB for 3 layers — acceptable on desktop).
2. Use the `pyscroll` library which solves this exact problem.

### 2.2 [P2] YAML re-loaded on every dialogue interaction
File: `engine/dialogue/dialogue_engine.py:47-74`

`resolve()` calls `yaml.safe_load` on the dialogue file every time the player presses ENTER. Cache loaded files by `dialogue_id` (invalidate only at scenario reload).

Same pattern: `engine/spell/spell_logic.py:_load_class_abilities` reloads class YAML every time the spell screen opens.

### 2.3 [P2] Map YAML opened twice during scene init
File: `engine/world/world_map_scene.py:177-196`

`_init()` calls `npc_loader.load_from_map(map_yaml_path)` and `item_box_loader.load_from_map(map_yaml_path)` (each opens the file), then opens the file directly twice more (lines 182-189 for BGM, 213-219 for spawn config). Four reads of the same file per map load. Open once and pass the parsed dict to each consumer.

### 2.4 [P2] Damage-float rendering re-renders text per frame
File: `engine/battle/battle_renderer.py:408-416`

```python
for f in state.damage_floats:
    shadow = self._assets.font_dmg.render(f.text, True, (0, 0, 0))
    ...
    surf = self._assets.font_dmg.render(f.text, True, f.color)
```

Each damage float re-renders both surfaces every frame, then blits the shadow 5 times. Text doesn't change after creation; cache the rendered surfaces on the `DamageFloat` itself or a parallel cache keyed on `id(f)`. Major savings during burst combat.

### 2.5 [P2] Per-frame allocations in renderers
- `WorldMapRenderer.render` allocates a fresh `pygame.Surface` for the fade overlay every frame when `fade_alpha > 0` (`world_map_renderer.py:94-99`). Allocate once, reuse, just refill the alpha.
- `BattleRenderer._draw_enemy` does `img.copy()` for KO alpha and another `sprite.copy()` for the hit-flash overlay every frame (`battle_renderer.py:117-120`, `397-400`). Pre-bake the KO ghost when `is_ko` flips; use a single shared overlay surface for the flash.
- `_render_quit_confirm` allocates a full-screen `SRCALPHA` overlay every frame the dialog is open (`world_map_renderer.py:119`).

### 2.6 [P2] WorldMapScene rebuilds visibility lists redundantly
File: `engine/world/world_map_scene.py:600-651`

`update()` builds `npc_rects`, `visible_npcs`, plus iterates NPCs again O(n²) for `other_rects`. `render()` rebuilds the same `visible_npcs` and `visible_boxes` lists. Compute once per frame (cache on the scene, invalidated when flags change), or pre-filter into stable per-frame collections.

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

### 3.4 [P2] YAML loaders share boilerplate

`npc_loader`, `item_box_loader`, `portal_loader`, `encounter_zone_loader`, `enemy_loader`, `dialogue_engine`, `item_catalog`, `item_effect_handler`, `spell_logic._load_class_abilities`, `world_map_logic.load_inn_cost / load_shop_items / load_recipes / load_magic_cores`, and `WorldMapScene._init` all open YAML with the same `with open(...) as f: yaml.safe_load(f)` pattern. Centralize as `engine/io/yaml_loader.py`:

```python
def load_yaml(path: Path, default=None) -> Any: ...
def load_yaml_required(path: Path) -> Any: ...   # raises with helpful path msg
```

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

### 4.1 [P1] `engine/world/world_map_scene.py` (679 lines, 35 methods)

Mixes: scene wiring, overlay lifecycle (save modal / dialogue / mc_shop / inn / item_shop / apothecary / item_box / quit_confirm), interact dispatch, fade transitions, battle launch from collision, scene init/asset loading, and update/render plumbing.

Proposed split:
- `engine/world/world_map_scene.py` — keep the `Scene` interface (events/update/render delegation, ~150 lines).
- `engine/world/world_map_overlay_stack.py` — the 7 overlays' open/close/event-routing currently spread across `_open_*`, `_close_*`, and the `if self._dialogue: ...` event chain. Replace with a small overlay stack (`push(overlay)`, `pop()`).
- `engine/world/world_map_init.py` — `_init`, `_build_spawner`, `_load_protagonist_sprite`.
- `engine/world/world_map_battle_launcher.py` — `_launch_battle_from_enemy` (which itself has formation-vs-boss branching that wants a service).
- `engine/world/fade_controller.py` — fade alpha + pending transition state machine.

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

1. **Bug fixes (1.1, 1.2, 1.4, 1.5, 1.6 callout, 1.8)** — small, isolated, with tests added per §5.6.
2. **Centralize YAML loading (3.4)** — paves the way for caching (§2.2, §2.3).
3. **Tile rendering refactor (2.1)** — biggest single perf win; need to confirm the integration with debug overlays and y-sort.
4. **Damage-float caching + fade-overlay reuse (2.4, 2.5)** — easy after #2.
5. **Break up `world_map_scene` (4.1)** — biggest readability win, unblocks future scene additions.
6. **Extract menu/list shared code (3.1)** — let the WizardScene base land before splitting equip/spell scenes per §4.4.
7. **Break up `battle_scene` and `battle_renderer` (4.2, 4.3)** — independent of #5/#6.
8. **Test gaps (§5)** — driven alongside each refactor; do not ship #5 or #7 without their corresponding test additions.

---

## 7. Out of scope (noted, not pursued)

- The `.get(k, default)` audit (§3.7) is a project-wide policy enforcement task that touches dozens of files; recommend a separate ticket.
- Test directory reorganization (§5.7) — already on the team's radar per CLAUDE.md.
- The 5 ~300-line files in §4.7 — under threshold; revisit when they cross 400.
