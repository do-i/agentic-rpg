# Refactoring Plan — July 2026

Findings from a code-quality scan (session: fable-rpg-refactoring). Work items are
ordered smallest-risk first. Each item is committed separately and checked off here
on completion. Delete this file when all items are done.

## Items

- [x] **1. `EngineConfigData.load` — declarative extraction/validation**
  Done: spec-table extraction; missing font sizes now raise like other keys (new test).
  Note: the `debug` block stays optional-with-off-default — codified by
  `test_debug_block_is_optional`, so kept as a deliberate exception.
  `engine/settings/engine_config_data.py:41` — 82 lines / 28 branches of copy-paste
  (`.get` → if-None → append-missing, ×13). Replace with a spec table
  (dotted path, type) driving both extraction and validation. Make error handling
  uniform: missing font sizes currently only print to stderr while other keys raise;
  `debug.party` / `debug.collision` use forbidden `.get(k, False)` fallbacks — all
  missing keys must raise with file/property/example.

- [x] **2. `ItemEffectHandler.apply_to_target` — dispatch table + target Protocol**
  Done: per-effect methods behind a class-level dispatch dict (class-level because
  tests build instances via `__new__`); shared `_strip_statuses` helper; unknown
  effects now raise at YAML load time and in `apply_to_target`; added `EffectTarget`
  Protocol documenting the MemberState/Combatant contract.
  `engine/item/item_effect_handler.py:142` — if/elif ladder over effect strings with
  `hasattr` duck-typing. Move each effect to a small method behind a dispatch dict;
  raise on unknown effect names (currently silently returns "" and masks YAML typos).
  Add a Protocol for the MemberState/Combatant target contract.

- [x] **3. Rename private cross-module import `_is_player_facing`**
  Done: renamed to `is_player_facing` across world_map_logic/renderer/scene.
  `engine/world/world_map_logic.py` exports `_is_player_facing`, imported by
  `world_map_scene.py:43`. Rename to `is_player_facing`.

- [ ] **4. `WorldMapScene.__init__` — 31 params, 18 hardcoded defaults**
  `engine/world/world_map_scene.py:67` — violates no-hardcoded-defaults rule
  (`screen_width=1280`, `text_speed="fast"`, `enemy_spawn_global_interval=30.0`, …).
  Drop all defaults; make `| None = None` collaborators required (AppModule always
  provides them); pass settings objects instead of exploded scalars where practical.
  Same treatment for the milder cases if time allows: `npc.py:67`, `battle_scene.py:47`,
  `player.py:81`, `enemy_sprite.py:67`.

- [ ] **5. `ItemShopRenderer.render` — 21 params → view-model dataclass**
  `engine/shop/item_shop_renderer.py:90` — scene marshals 20 args per frame. Introduce
  a frame view-state dataclass built by the scene; split the 131-line body into
  layout / header / list / party-preview / footer / overlay helpers.

- [ ] **6. Shop scene state machines — shared states + qty/popup handling**
  `item_shop_scene.py`, `apothecary_scene.py`, `magic_core_shop_scene.py` each
  hand-roll stringly `self._state` ("list"/"qty"/"popup"/…) with near-identical
  popup-dismiss and qty-picker key handling. Extract shared state constants and a
  mixin/base for the common sub-states (pattern precedent: `MenuSfxMixin`).
  Renderers: move duplicated qty-overlay/popup drawing into `shop_renderer.py`.

- [ ] **7. Split branchy battle/world helpers**
  `battle_enemy_logic.py:15` `resolve_enemy_turn` (60 lines / 15 branches),
  `sign_locator.py:22` `find_sign_tiles` (15 branches) — split selection /
  targeting / resolution phases into small functions.
