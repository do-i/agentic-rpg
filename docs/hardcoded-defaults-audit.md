# Hardcoded Defaults Audit

Audit of hardcoded default values found in the engine codebase. Intended as input
for a follow-up refactor session that moves these into authoritative sources
(`settings.yaml`, `manifest.yaml`, scenario data YAML, or dedicated design docs).

Conventions used in the **Should live in** column:
- `settings.yaml` — engine runtime config (`engine/settings/settings.yaml`).
- `manifest.yaml` — scenario-level manifest (`rusted_kingdoms/manifest.yaml`).
- `<yaml-loader>` — already read from YAML; the hardcoded value is the
  *fallback* when the field is missing. Decide whether the field should be
  required (raise) or documented/seeded in the YAML schema.
- `design-doc:NN-xxx.md` — constant belongs with documented game design; either
  move into scenario YAML (balance) or keep in code but cross-link the doc.

Severity legend:
- **H (high)**: game-balance / tunable — should absolutely live in YAML.
- **M (medium)**: engine config — belongs in `settings.yaml` or a schema
  contract that forbids silent defaults.
- **L (low)**: pure visual / UI layout constant — fine in code, but flag for
  theming if ever needed.

---

## 1. Method parameter defaults

| File | Line | Parameter / default | Should live in | Sev |
|------|------|--------------------|----------------|-----|
| engine/app_module.py | 40 | `mode: str = "normal"` | CLI arg contract (not a fallback) | L |
| engine/app_module.py | 40 | `recording_file: str = "recording.pkl"` | `settings.yaml` (new `record.file`) or CLI only | M |
| engine/app_module.py | 40 | `playback_speed: float = 1.0` | CLI arg contract | L |
| engine/audio/bgm_manager.py | 43 | `play(loops: int = -1, fade_ms: int = 1000)` | `settings.yaml` (audio.bgm.fade_ms) | L |
| engine/audio/bgm_manager.py | 54 | `play_key(loops: int = -1, fade_ms: int = 1000)` | `settings.yaml` (audio.bgm.fade_ms) | L |
| engine/audio/bgm_manager.py | 62 | `stop(fade_ms: int = 500)` | `settings.yaml` (audio.bgm.stop_fade_ms) | L |
| engine/battle/battle_fx.py | 61 | `flash(duration=FLASH_DURATION, color=FLASH_COLOR)` | design-doc:03-Battle.md (FX section) | L |
| engine/battle/battle_fx.py | 65 | `shake(duration=SHAKE_DURATION, amplitude=SHAKE_AMPLITUDE)` | design-doc:03-Battle.md | L |
| engine/battle/battle_logic.py | 47 | `resolve_action(..., screen_width: int = 1280, ...)` | `settings.yaml` (display.screen_width) — should be threaded, not hardcoded | **H** |
| engine/battle/battle_scene.py | 341 | `_enter_resolve(is_enemy: bool = False)` | Call-site explicit | L |
| engine/common/font_provider.py | 23 | `get(size: int, bold: bool = False)` | Call-site explicit | L |
| engine/party/repository_state.py | 26 | `__init__(gp: int = 0, ...)` | scenario new-game YAML (starting gp) | M |
| engine/party/repository_state.py | 57 | `add_item(qty: int = 1)` | Call-site explicit | L |
| engine/party/repository_state.py | 95 | `has_item(qty: int = 1)` | Call-site explicit | L |
| engine/party/repository_state.py | 101 | `sell_item(qty: int = 1)` | Call-site explicit | L |
| engine/record/recorder.py | 28 | `__init__(playback_speed: float = 1.0)` | CLI arg contract | L |
| engine/record/recorder.py | 48 | `get_events(delta: float = 0.0)` | Call-site explicit | L |
| engine/util/frame_clock.py | 9 | `__init__(fps: int = 60)` | `settings.yaml` (display.fps) — DI should inject | M |
| engine/util/pseudo_random.py | 26 | `choices(weights=None, k: int = 1)` | Matches stdlib `random.choices` — keep | L |
| engine/world/collision.py | 15 | `__init__(tile_size: int = 32)` | `settings.yaml` (tiles.tile_size) — DI should inject | M |
| engine/world/npc.py | 80-84 | `default_facing="down", anim_mode="still", anim_speed=1.0, wander_range=2, tile_size=32` | NPC YAML schema (`data/maps/*.yaml` npcs entry); `tile_size` from settings | **H** |
| engine/world/npc.py | 158 | `update(delta, near: bool = False, ...)` | Call-site explicit | L |
| engine/world/npc_loader.py | 18 | `__init__(tile_size: int = 32, ...)` | `settings.yaml` (tiles.tile_size) | M |

---

## 2. YAML fallback defaults (`.get("key", <default>)`)

These silently succeed when the YAML schema omits the key. For each, decide:
*(a) make the key required & raise if missing, or (b) document the default in
the schema/design-doc.*

| File | Line | Key & default | Source YAML | Sev |
|------|------|--------------|-------------|-----|
| engine/battle/battle_enemy_logic.py | 28 | `action.get("action", "attack")` | enemies_rank_*.yaml (ai.moves) | M |
| engine/battle/battle_enemy_logic.py | 88 | `ai_block.get("pattern", "random")` | enemies_rank_*.yaml (ai.pattern) | M |
| engine/battle/battle_enemy_logic.py | 112 | `turn_mod.get("every", 1)` | enemies_rank_*.yaml (condition.turn_mod) | M |
| engine/battle/battle_enemy_logic.py | 123 | `m.get("weight", 1)` | enemies_rank_*.yaml (ai.moves.weight) | M |
| engine/battle/battle_enemy_logic.py | 135 | `targeting.get("default", "random_alive")` | enemies_rank_*.yaml (targeting.default) | M |
| engine/battle/battle_logic.py | 55 | `action.get("type", "attack")` | runtime state (not YAML) | L |
| engine/battle/battle_logic.py | 74 | `ab.get("type", "spell")` | classes/*.yaml (abilities.type) | M |
| engine/battle/battle_logic.py | 76 | `ab.get("name", "Spell")` | classes/*.yaml (abilities.name) — should be required | **H** |
| engine/battle/battle_logic.py | 79 | `ab.get("mp_cost", 0)` | classes/*.yaml (abilities.mp_cost) | **H** |
| engine/battle/battle_logic.py | 172 | `item.get("qty", 1)` | enemies_rank_*.yaml (drops.items.qty) | M |
| engine/battle/battle_rewards.py | 165-167 | `mc.get("size", "S")`, `mc.get("qty", 1)` | enemies_rank_*.yaml (drops.mc) | M |
| engine/battle/battle_rewards.py | 176 | `item_totals.get(item_id, 0)` | runtime accumulator — fine | L |
| engine/battle/battle_rewards.py | 196 | `entry.get("weight", 1)` | enemies_rank_*.yaml (drops.items.weight) | M |
| engine/battle/battle_renderer.py | 315 | `action.get("data", {}).get("name", "Attack")` | classes/*.yaml (abilities.name) | M |
| engine/battle/battle_renderer.py | 357 | `item.get("disabled", False)` | runtime UI state — fine | L |
| engine/battle/enemy_loader.py | 68-80 | `hp=10, atk=5, def_=3, mres=2, dex=8, boss=False, sprite_scale=100, exp_yield=0` | enemies_rank_*.yaml — **should be required** | **H** |
| engine/battle/battle_scene.py | 185 | `ab.get("mp_cost", 0)` | classes/*.yaml (abilities.mp_cost) | **H** |
| engine/battle/battle_scene.py | 207 | `TARGET_MAP.get(defn.target, "single_ally")` | items/*.yaml (field_use target) | M |
| engine/battle/battle_scene.py | 248 | `ab_data.get("target", "single_enemy")` | classes/*.yaml (abilities.target) | M |
| engine/battle/post_battle_scene.py | 174 | `item.get('qty', 1)` | reward dict — fine | L |
| engine/common/map_state.py | 56 | `data.get("position", [0, 0])` | save YAML / manifest.start.position | M |
| engine/dialogue/dialogue_engine.py | 102 | `gift.get("qty", 1)` | dialogue/*.yaml (give_items.qty) | M |
| engine/encounter/encounter_manager.py | 69-70 | `mc.get("size", "S")`, `mc.get("qty", 1)` | battle reward dict | L |
| engine/encounter/encounter_manager.py | 113 | `ab.get("unlock_level", 1)` | classes/*.yaml (abilities.unlock_level) | **H** |
| engine/encounter/encounter_zone_loader.py | 25 | `entry.get("chase_range", 0)` | encount/*.yaml (entries.chase_range) | **H** |
| engine/encounter/encounter_zone_loader.py | 37 | `raw_boss.get("once", True)` | encount/*.yaml (boss.once) | M |
| engine/encounter/encounter_zone_loader.py | 45 | `b.get("blocked_message", "A mysterious force blocks your attack.")` | encount/*.yaml (barrier_enemies.blocked_message) | **H** (content string in code) |
| engine/encounter/encounter_zone_loader.py | 55 | `data.get("density", 0.5)` | encount/*.yaml (density) | **H** |
| engine/io/game_state_loader.py | 133 | `repo_data.get("gp", 0)` | save YAML | L |
| engine/io/game_state_loader.py | 138 | `item.get("qty", 1)` | save YAML | L |
| engine/io/game_state_loader.py | 140 | `item.get("locked", False)` | save YAML | L |
| engine/item/item_catalog.py | 67 | `entry.get("name", item_id.replace("_", " ").title())` | items/*.yaml (name) — should be required | **H** |
| engine/item/item_catalog.py | 70 | `entry.get("sell_price", 0) or 0` | items/*.yaml (sell_price) | M |
| engine/item/item_catalog.py | 73-74 | `sellable=True, droppable=True` | items/*.yaml | M |
| engine/item/item_effect_handler.py | 44-48 | `target="single_alive", amount=0, revive_hp_pct=0.0, consumable=True` | items/field_use.yaml | M |
| engine/item/magic_core_catalog_state.py | 26 | `entry.get("exchange_rate", 0)` | items/magic_cores.yaml (exchange_rate) — should be required | **H** |
| engine/shop/apothecary_renderer.py | 171 | `output.get("qty", 1)` | recipe/*.yaml (output.qty) | M |
| engine/shop/apothecary_renderer.py | 173,209 | `recipe.get("gp_cost", 0)`, `sel.get("gp_cost", 0)` | recipe/*.yaml (gp_cost) — required | **H** |
| engine/shop/apothecary_renderer.py | 212 | `output.get("qty", 1)` | recipe/*.yaml (output.qty) | M |
| engine/shop/apothecary_scene.py | 110,206 | `recipe.get("gp_cost", 0)` | recipe/*.yaml (gp_cost) | **H** |
| engine/shop/apothecary_scene.py | 226 | `output.get("qty", 1)` | recipe/*.yaml (output.qty) | M |
| engine/shop/item_shop_renderer.py | 142,165 | `item.get("buy_price", 0)`, `sel.get("buy_price", 0)` | data/maps/*.yaml (shop.items.buy_price) | **H** |
| engine/shop/item_shop_scene.py | 90 | `item.get("name", item["id"].replace("_", " ").title())` | items/*.yaml | M |
| engine/shop/item_shop_scene.py | 130,145,190 | `sel.get("buy_price", 0)` | data/maps/*.yaml (shop.items.buy_price) | **H** |
| engine/status/status_logic.py | 34 | `ab.get("unlock_level", 1)` | classes/*.yaml (abilities.unlock_level) | **H** |
| engine/status/status_logic.py | 42 | `spell.get("target", "single_ally")` | classes/*.yaml (abilities.target) | M |
| engine/status/status_logic.py | 52,78 | `spell.get("mp_cost", 0)` | classes/*.yaml (abilities.mp_cost) | **H** |
| engine/status/status_logic.py | 60,79 | `spell.get("heal_coeff", 1.0)` | classes/*.yaml (abilities.heal_coeff) | **H** |
| engine/status/status_scene.py | 137,140 | `spell.get("mp_cost", 0)`, `spell.get("target", "single_ally")` | classes/*.yaml | M |
| engine/status/status_renderer.py | 290 | `spell.get("mp_cost", 0)` | classes/*.yaml | M |
| engine/world/item_box_loader.py | 58 | `entry.get("id", "unknown")` | data/maps/*.yaml (item_boxes.id) — required | **H** |
| engine/world/item_box_loader.py | 59 | `entry.get("position", [0, 0])` | data/maps/*.yaml (item_boxes.position) — required | **H** |
| engine/world/item_box_loader.py | 64,75 | `item.get("qty", 1)`, `mc.get("qty", 1)` | data/maps/*.yaml (item_boxes.loot.*.qty) | M |
| engine/world/npc_loader.py | 36 | `entry.get("id", "unknown")` | data/maps/*.yaml (npcs.id) — required | **H** |
| engine/world/npc_loader.py | 38 | `entry.get("position", [0, 0])` | data/maps/*.yaml (npcs.position) — required | **H** |
| engine/world/npc_loader.py | 40 | `entry.get("default_facing", "down")` | data/maps/*.yaml (npcs.default_facing) | M |
| engine/world/npc_loader.py | 44-46 | `mode="still", speed=1.0, range=2` | data/maps/*.yaml (npcs.animation) | M |
| engine/world/world_map_logic.py | 146 | `transition.get("position", [0, 0])` | data/maps/*.yaml (transition.position) — required | **H** |
| engine/world/world_map_logic.py | 155 | `map_data.get("inn", {}).get("cost", 50)` | data/maps/*.yaml (inn.cost) — should be required | **H** |
| engine/world/world_map_logic.py | 186 | `d.get("exchange_rate", 0)` | items/magic_cores.yaml | M |
| engine/world/world_map_renderer.py | 70 | `box_opened.get(box.id, False)` | runtime save state — fine | L |

---

## 3. Module-level constants (game balance / tuning)

High-priority — these are tunable numbers, not layout. They read like design
knobs but are compiled into the engine.

| File | Line | Constant | Value | Should live in | Sev |
|------|------|----------|-------|----------------|-----|
| engine/battle/battle_logic.py | 206 | `FLEE_BASE_CHANCE` | `0.30` | design-doc:03-Battle.md → scenario YAML (battle.yaml) | **H** |
| engine/battle/battle_logic.py | 207 | `FLEE_ROGUE_DEX_BONUS` | `0.02` | design-doc:03-Battle.md → scenario YAML | **H** |
| engine/battle/battle_rewards.py | 31 | `EXP_CAP` | `1_000_000` | design-doc:02-Characters.md → scenario YAML | **H** |
| engine/battle/battle_rewards.py | 32 | `LEVEL_CAP` | `100` | scenario YAML (characters/progression.yaml) | **H** |
| engine/battle/battle_rewards.py | 34-40 | `CLASS_EXP_BASE` dict | `{hero:100,...}` | **classes/*.yaml** (per-class) — duplicated with party_state | **H** |
| engine/battle/battle_rewards.py | 41 | `EXP_FACTOR` | `2.0` | scenario YAML | **H** |
| engine/party/party_state.py | 44-50 | `_CLASS_EXP_BASE` dict | duplicate of above | classes/*.yaml (dedupe) | **H** |
| engine/party/party_state.py | 51 | `_EXP_FACTOR` | `2.0` | scenario YAML (dedupe) | **H** |
| engine/party/party_state.py | 52 | `LEVEL_CAP` | `100` | scenario YAML (dedupe) | **H** |
| engine/party/repository_state.py | 15 | `GP_CAP` | `8_000_000` | design-doc:09-Currency.md → scenario YAML | **H** |
| engine/party/repository_state.py | 16 | `ITEM_QTY_CAP` | `100` | design-doc:04-Bag.md → scenario YAML | **H** |
| engine/party/repository_state.py | 17 | `MAX_TAGS_PER_ITEM` | `5` | design-doc:04-Bag.md → scenario YAML | **H** |
| engine/shop/magic_core_shop_scene.py | 16 | `LARGE_RATE_THRESHOLD` | `1_000` | design-doc:14-Shop.md → scenario YAML | **H** |
| engine/shop/magic_core_shop_scene.py | 18-19 | `QTY_STEP_SMALL=1, QTY_STEP_LARGE=10` | — | settings.yaml (shop.qty_step_*) | M |
| engine/shop/item_shop_scene.py | 18-19 | `QTY_STEP_SMALL=1, QTY_STEP_LARGE=5` | — | settings.yaml (shop.qty_step_*) | M |
| engine/encounter/enemy_spawner.py | 27 | `ROGUE_CHASE_REDUCTION` | `2` tiles | scenario YAML (party mechanics) | **H** |
| engine/encounter/enemy_spawner.py | 28 | `STEALTH_CLOAK_REDUCTION` | `3` tiles | items/*.yaml (accessory effect) | **H** |
| engine/encounter/enemy_spawner.py | 29 | `LURE_CHARM_INTERVAL_MULT` | `0.5` | items/*.yaml (accessory effect) | **H** |
| engine/io/save_manager.py | 18 | `AUTOSAVE_INDEX` | `0` | settings.yaml (saves.autosave_slot) | M |
| engine/io/save_manager.py | 19 | `PLAYER_SLOT_COUNT` | `100` | settings.yaml (saves.slot_count) | M |
| engine/title/name_entry_scene.py | 15 | `NAME_MAX_LENGTH` | `12` | settings.yaml or scenario YAML | M |
| engine/world/player.py | 9 | `PLAYER_SPEED` | `5` | scenario YAML (party/mechanics) | **H** |
| engine/world/player.py | 10-11 | `PLAYER_WIDTH, PLAYER_HEIGHT` | `64, 64` | settings.yaml (player.sprite_size) — tied to sprite format | M |
| engine/world/player.py | 13-14 | `COLLISION_W, COLLISION_H` | `20, 18` | settings.yaml (player.collision_*) | M |
| engine/world/player.py | 18 | `DEBUG_COLLISION` | `True` | settings.yaml (debug.collision) — currently always on! | **H** |
| engine/world/portal_data.py | 6 | `PORTAL_TRIGGER_RADIUS` | `8` px | settings.yaml (world.portal_trigger_radius) | M |
| engine/world/npc.py | 17 | `NPC_SIZE` | `64` | settings.yaml (npc.sprite_size) | M |
| engine/world/npc.py | 25 | `BASE_FRAME_DUR` | `0.15` | settings.yaml (npc.anim.frame_dur) | M |
| engine/world/npc.py | 28-29 | `WANDER_PAUSE_MIN/MAX` | `1.0, 3.5` | settings.yaml (npc.wander.*) | M |
| engine/world/npc.py | 32-33 | `NPC_COLLISION_W/H` | `20, 18` | settings.yaml (npc.collision_*) — duplicated w/ player | M |
| engine/world/animation_controller.py | 6 | `FRAME_DURATION` | `0.1` | settings.yaml (anim.frame_duration) — must match TSX | M |
| engine/world/sprite_sheet.py | 19-21 | `FRAME_WIDTH=64, FRAME_HEIGHT=64, FRAMES_PER_ROW=9` | — | manifest.yaml (sprite.frame_layout) — tied to art pipeline | M |
| engine/encounter/enemy_sprite.py | 21-37 | duplicates of player/npc sprite+collision+anim constants | — | settings.yaml (dedupe with npc.py / player.py) | M |
| engine/audio/bgm_manager.py | 14 | `SOUND_VOLUME` | `0.3` | settings.yaml (audio.bgm_volume) | M |
| engine/audio/sfx_manager.py | 13 | `SFX_VOLUME` | `0.8` | settings.yaml (audio.sfx_volume) | M |
| engine/battle/battle_fx.py | 13-16 | `FLASH_DURATION/SHAKE_DURATION/AMPLITUDE/FREQ` | — | settings.yaml (battle.fx.*) | L |
| engine/common/target_select_overlay_renderer.py | 31 | `HP_LOW_THRESHOLD` | `0.35` | duplicated with color_constants.py:10 — dedupe | M |
| engine/common/color_constants.py | 10 | `HP_LOW_THRESHOLD` | `0.35` | settings.yaml (ui.hp_low_threshold) | M |
| engine/record/record_format.py | 3 | `RECORDING_VERSION` | `4` | code only — protocol version | L |
| engine/game.py | 10-11 | `_REPEAT_DELAY=0.25, _REPEAT_INTERVAL=0.07` | — | settings.yaml (input.key_repeat_*) | M |

---

## 4. `EngineConfigData.load()` — defensive fallback defaults

`engine/settings/engine_config_data.py` itself contains hardcoded fallbacks for
keys the YAML schema says are required. If settings.yaml is authoritative,
these should raise instead of silently defaulting.

| Line | Field | Fallback | Fix |
|------|-------|----------|-----|
| 45 | `smooth_collision` | `True` | raise on missing |
| 46 | `mc_exchange_confirm_large` | `True` | raise on missing |
| 47 | `use_aoe_confirm` | `True` | raise on missing |
| 51 | `debug.party` | `False` | keep (truly optional) |
| 52 | `enemy_spawn.global_interval` | `30.0` | raise on missing |
| 78 | `screen_width` | `1280` | raise on missing |
| 79 | `screen_height` | `766` | raise on missing |
| 80 | `fps` | `60` | raise on missing |
| 81 | `tile_size` | `32` | raise on missing |

---

## 5. UI layout constants (intentionally in code)

Listed for completeness — NOT recommended to move to YAML. Flag if theming
is ever needed.

- `engine/status/status_renderer.py:42-56` — PAD_X/Y, ROW_H, column widths
- `engine/status/status_scene.py:19` — POPUP_W
- `engine/world/item_box_scene.py:12-16` — MODAL_W, ROW_H, TITLE_H, HINT_H, PAD
- `engine/shop/shop_constants.py:22-24` — MODAL_W, HEADER_H, ROW_GAP
- `engine/shop/apothecary_renderer.py:32-36` — PAD, SPRITE_SIZE, FOOTER_H, VISIBLE_ROWS, POPUP_W
- `engine/shop/magic_core_shop_renderer.py:31-33` — PAD, FOOTER_H, VISIBLE_ROWS
- `engine/shop/item_shop_renderer.py:30-34` — PAD, SPRITE_SIZE, FOOTER_H, VISIBLE_ROWS, POPUP_W
- `engine/battle/constants.py:8-9` — ENEMY_AREA_H, ROW_H
- `engine/battle/battle_renderer_constants.py:11-13` — PORTRAIT_SIZE, ROW_PAD, BAR_H
- `engine/title/save_modal_scene.py:10-19` — MODAL dims, SLOT_HEIGHT, VISIBLE_SLOTS
- `engine/title/load_game_scene.py:12-15` — SLOT_HEIGHT, VISIBLE_SLOTS, MODAL dims
- `engine/title/menu_renderer.py:6-7` — _DEFAULT_CURSOR_W, _CURSOR_PAD
- `engine/dialogue/dialogue_scene.py:15-18` — BOX_H, MARGIN, PAD, PORTRAIT_SIZE
- `engine/item/item_renderer.py:57-70` — PAD, HEADER_H, TAB_H/GAP, row sizes, button sizes
- `engine/inn/inn_scene.py:32-39` — MODAL, PAD, HEADER, SPRITE, ROW, BAR, FOOTER, POPUP
- `engine/battle/post_battle_scene.py:28-29` — PAD, ROW_H
- `engine/common/item_selection_view.py:46-50` — PEEK_RATIO, ROW_INSET_X, CURSOR_X, CONTENT_X, RIGHT_PAD
- `engine/common/target_select_overlay_renderer.py:34-42` — MODAL/ROW/PAD/HEADER/FOOTER/BAR/WARN layout
- `engine/world/world_map_logic.py:21` — FADE_SPEED

---

## 6. Recommended refactor priorities

1. **Balance constants into scenario YAML** (Sev **H** in §3): EXP/LEVEL caps,
   flee formula, GP/qty caps, CLASS_EXP_BASE (currently duplicated between
   `battle_rewards.py` and `party_state.py`), accessory modifiers in
   `enemy_spawner.py`, `PLAYER_SPEED`, `DEBUG_COLLISION`.
2. **Required YAML fields should raise, not default** (§2 **H** rows): enemy
   stats, ability `name`/`mp_cost`/`unlock_level`, shop `buy_price`, recipe
   `gp_cost`, item `name`, item_box/npc `id`/`position`, transition
   `position`, inn `cost`, zone `density`, `chase_range`, barrier
   `blocked_message`, magic core `exchange_rate`.
3. **Threaded settings instead of parameter defaults** (§1 M): `tile_size`,
   `fps`, `screen_width` in `resolve_action`. DI already has
   `EngineConfigData`; thread it through instead of duplicating fallbacks.
4. **EngineConfigData fallbacks** (§4): drop the fallbacks for keys the loader
   already validates as required; keep only the truly optional ones.
5. **Dedupe**: `HP_LOW_THRESHOLD` (2 files), `CLASS_EXP_BASE`/`LEVEL_CAP`/
   `EXP_FACTOR` (2 files), NPC collision/sprite constants duplicated in
   `npc.py` / `enemy_sprite.py` / `player.py`.
6. **UI constants** (§5): leave alone unless a theming system is planned.
