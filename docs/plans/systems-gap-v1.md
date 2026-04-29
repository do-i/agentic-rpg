# Systems Gap Analysis — v1

One-line gap summary per design doc, grouped by `docs/design/INDEX.md`. Action = **doc** (update doc to match code), **code** (implement what doc specifies), or **either** (decision needed).

Legend: ✅ aligned · ⚠ minor drift · ❌ significant gap

---

## Core

### architecture.md ❌
- **Tech stack mismatch**: doc lists Pygame-CE, `RestrictedPython` sandbox, `hatch` build, Python 3.11+; `pyproject.toml` uses vanilla `pygame==2.6.1`, `setuptools`, no scripting sandbox, requires-python `>=3.14.3`. → **doc**.
- **Architecture diagram says "Scenario API"**: there is no scripting API; scenarios are pure YAML/TMX data. → **doc**.

### save.md ❌
- **Filename format**: doc specifies `YYYY-MM-DD-HH-MM-SS-[CRC32].yaml`; code uses `{slot_index:03d}.yaml` with checksum embedded inside YAML. → **doc**.
- **Saved fields**: doc schema includes `abilities_unlocked`, `status_effects`, `map.visited`; `_serialize` in `save_manager.py` writes none of these. Code adds `opened_boxes`, `exp_next` not in doc. → **doc** (status_effects intentional? **either** for abilities_unlocked / visited).
- **Equipped fields not serialized per-member**: actually `equipped` is serialized — ✅.

### scenario.md ⚠
- Doc is mostly a stub (“See story_content”). Manifest has fields not described: `engine_managed_flags`, `apothecary`, `inn`, `item_shop`, `item_box`, `title`, `font`. → **doc** (expand schema).


### validation.md ⚠
- `tools/validate.py` implements broken-link + flag-audit passes. Doc table lists `recipe/*.yaml` `inputs.items[].id` and `output.item` — verify these are traversed. Doc omits encounter zone references (`enemy_id`, `loot_table.item`) that live in `data/encount/` and `data/enemies/`. → **doc** (extend reference-types table to match what validator actually checks).

---

## Combat

### battle.md ❌
- **Row system (front/back, attack_range)**: doc specifies row-based damage modifiers and an `attack_range: melee|ranged` ability field; **no row state on `MemberState`/`Combatant`, no `attack_range` handling anywhere**. → **code** (implement)
- **Encounter rate model**: doc defines `encounter_rate` (per map) + `encounter_modifier` from Rogue accessories with clamp formula; code uses tile-based `density`/`spawn_frequency` and a `stealth_cloak` *chase_range* reduction (`enemy_spawner.py`) — totally different model. → **doc** (rewrite to match tile-spawner reality).
- **Status effect cure matrix**: code has POISON/SILENCE/SLEEP/STUN/KNOCKBACK; cure-via-rest (inn full-restore) — verify InnScene clears statuses. → spot check.

### enemy.md ❌
- **Zone enemy rosters**: doc lists Wolf/Bat/Spider/Treant for Zone 1; YAML `zone_01_starting_forest.yaml` uses `goblin`/`goblin_warrier`. Every zone in doc is out of date. → **doc** (rewrite tables from current encounter YAMLs).
- **Schema for `mc_tier` vs `mc[].size/qty`**: doc shows both; code expects `drops.mc[].size/qty` (matches enemy YAML). Drop the `mc_tier` text. → **doc**.
- **Boss `ai_ref: boss_move_sets/<id>.yaml`**: directory `data/enemies/boss_move_sets/` exists; verify loader resolves it. → spot check.
- **Targeting overrides / behavior pattern**: doc lists `random_alive`, `lowest_hp`, `all_party`; code in `battle_enemy_logic.py` — verify coverage. Likely partial. → **either**.
- **Barrier enemies / `veil_breaker`**: encounter loader has `BarrierEnemy.requires_item`; verify wiring with item present-check (not consumed). → spot check.

### loot.md ✅
- D100 weighted resolution and "no-drop" via weights summing under 100 is implemented in `engine/util/weighted_pick.py` / drop-pool resolution. No-drop semantics — verify. → spot check.
- Per-zone MC drop tier table is informational, encoded directly per-enemy. ✅

### spells.md ⚠
- Doc table (20 spells, lvl 1/3/5/7… + ultimates at 46/48/50/52 with story-flag gate) matches `sorcerer.yaml` unlock_levels (1, 3, 5, 7, 10, 13, …, 46, 48, 50, 52).
- **Story-flag gate on ultimates**: doc says "ultimates gated by story flag"; class YAMLs only have `unlock_level`, no flag check. → **code** (add flag gate) or **doc** (drop the gate).

---

## World

### dialogue.md ⚠
- `type: npc` / `type: cutscene` model matches `DialogueEngine.resolve`. ✅
- **`on_complete` actions**: doc lists `set_flag, give_items, unlock, start_battle, join_party, transition`; code dispatches `set_flag, give_items, join_party, transition, start_battle, open_shop, open_inn, open_apothecary` — `unlock` is *not* implemented; `open_*` actions not in doc. → **doc** (add open_*; drop or implement `unlock`).
- "Actions fire once per dialogue play-through" — `give_items` example warns about farming; codebase relies on scenario-author guarding via flags (matches doc note). ✅

### map.md ❌
- **`world.yaml` referenced but missing**: doc says "See data/maps/world.yaml"; no such file in `rusted_kingdoms/data/maps/`. → **doc** (drop reference).
- **NPC `present.requires/excludes` visibility**: doc specifies the schema; verify `NpcLoader`/`Npc` honors it. Spot check needed. → spot check.
- **8-direction movement**: doc says 8 directions; `player.py` normalises diagonal speed → 8-way works. ✅

### npc.md ⚠
- Doc specifies `animation: { mode: still|step|wander, speed, range }`; verify `NpcLoader` reads these. `engine/world/npc.py` and `animation_controller.py` exist. → spot check; likely ✅.

### transportation.md ❌
- **Entire system unimplemented** (deferred to v2 per `systems-gap.md`): no transport scene, no `port_tiles`, no `world.yaml`, `MapState.visited` is collected but never used as warp source. → **code** (v2) — already tracked.

---

## Party & Items

### apothecally.md ⚠
- **Schema mismatch**: doc shows nested `unlock: { flag: ... }` and fields `output_name`, `locked_label_flavor`; YAML/code use flat `unlock_flag`. → **doc**.
- **`unique_output` guard** present in code + YAML (`recipe_veil_breaker`) but **not in doc**. → **doc** (add).
- **`phoenix_wing` as condition-check (not consumed) for `life_crystal`**: doc flags as open question; current `recipe_life_crystal` does not reference `phoenix_wing` at all. → **doc** (remove note or reflect decision).
- UI states (list/detail/popup), gp display, lock/unlock icons — all match. ✅

### bag.md ❌
- **Tag editing UI**: doc specifies `[Edit Tags]` panel with toggle for system tags + custom-tag creation; `item_scene.py`/`item_renderer.py` only display tags read-only — no edit flow. → **code** (build edit UI) or **doc** (drop UI spec).
- Repository data layer (`add_tag`, `remove_tag`, `set_locked`, `max_tags=5`, `items_by_tag`) is fully implemented. ✅
- "Sell UI: filter by tag" — verify in `item_shop_scene.py`. → spot check.

### characters.md ⚠
- Stats, exp curve `exp_base * level^exp_factor`, hp/mp growth (`con+6`, `int+6`), level cap 100, exp cap 1M, full restore on level-up — all implemented in `engine/party/`. ✅
- **Ability tables** (Power Strike, Rally, Limit Slash etc.) match `data/classes/hero.yaml`. ✅
- **`heal_pct` ability field** exists in `hero.yaml` (`second_wind`); verify resolver supports it (doc mentions `hp_max * heal_pct`). → spot check.
- Min/Max HP/MP table is informational target — values in YAML are authoritative. ✅

### currency.md ✅
- GP cap (8M), MC sizes XS/S/M/L/XL with ×10 ratio, magic core shop scene, GP shown in HUD. ✅
- "Tiered cores (small→GP, large→craft)" is design intent; engine doesn't restrict, scenario gates by recipe inputs. ✅

### equipment.md ⚠
- `EquipScene` exists; per-character gray-out, stat-diff preview, and item-shop buy/sell flow exist. ✅
- **Sell price = 0.5 × buy** — verify `ItemDef.sell_price` is auto-derived; code stores `sell_price` separately on item def (per-item override). Currently scenario YAMLs set `sell_price` explicitly. → **doc** (drop "0.5 buy auto-derive" claim) or **code** (default rule).
- `class_restriction`: actual field is `equippable: [classes]` in `hero.yaml`. → **doc** (correct field name).

### party.md ⚠
- Composition (1 protagonist + 4 supports), exp-equal-split, KO=0 EXP, level cap 100, exp cap 1M, gp cap 8M, stat cap 100, item cap 100 — all enforced via `BalanceData` and `RepositoryState`. ✅
- **Row formation (front/back) + flee_rate / encounter_modifier / trap_detect**: only flee_rate (Rogue dex bonus) implemented; row + encounter_modifier + trap_detect not implemented. → **code** or **doc** (drop unimplemented).
- **Status effects table**: doc lists `taunt`, `def_up`; combat enums (`StatusEffect`) include POISON/SLEEP/STUN/SILENCE/KNOCKBACK only. → **doc** (drop taunt/def_up) or **code**.
- **Phoenix Down equivalent** for KO revive: verify item exists in `consumables_recovery.yaml`. → spot check.

### shop.md ⚠
- `unlock_flag`-gated shop items in map YAML — implemented. ✅
- **"Every rest triggers full restock"**: verify `InnScene` calls into shop state to restock. → spot check; likely missing. → **code** or **doc** (drop restock semantics).

---

## UI

### screen.md ⚠
- World map / dialogue box / battle / status / equipment / item / pause-menu screens all implemented at the scene level. ✅
- **Resolution / font / portrait choices** still listed as "decisions to confirm"; engine ships at fixed resolution from `Settings`/`EngineSettings`. → **doc** (record final choices).
- **Layer model `ground/mid/top/ui` + Y-sort**: implemented in world rendering. ✅
- **Item filter tabs (All/Recovery/Status/Battle/Key)**: verify in `item_renderer.py`; current UI shows tag list but no tab filter. → **code** or **doc**.

### sprites.md ✅
- Pure scenario reference (LPC URLs); no engine claims to verify. ✅

---

## Cross-cutting Notes

1. **Stale CLAUDE.md package layout**: `engine/dto/`, `engine/service/`, `engine/ui/` directories no longer exist; code is reorganised into per-feature packages (`engine/party/`, `engine/item/`, `engine/shop/`, etc.). → **doc** (update `CLAUDE.md`, not under `docs/design/`).
2. **`status_effects` in saves**: design assumes persistence; serializer does not write them. Likely intentional (statuses cleared on save?) — confirm and document. → **doc**.
3. **`engine_managed_flags` in manifest** (`story_act2_started` … `boss_zone10_defeated`) — undocumented mechanism by which the engine auto-fires act flags; not present in `flag.md` or `scenario.md`. → **doc**.

---

## Recommended Quick Wins (doc-only)

1. Rewrite `architecture.md` tech-stack table.
2. Replace `enemy.md` zone tables with current YAML rosters.
3. Update `apothecally.md` schema to match flat `unlock_flag` + add `unique_output`.
4. Update `save.md` filename + serialized-fields list.
5. Update `dialogue.md` `on_complete` action table to include `open_shop/open_inn/open_apothecary` and drop `unlock`.
6. Update `equipment.md` field name `class_restriction` → `equippable`.
7. Replace `battle.md` encounter-rate section with the tile-spawner / `density` / `chase_range` model.
8. Update `CLAUDE.md` package layout.

## Recommended Code Decisions (need user input)

1. Row / `attack_range` system — implement or drop from `battle.md` + `party.md`?
2. Tag-editing UI in item screen — implement or drop from `bag.md`?
3. Ultimate-spell story-flag gate — implement or drop from `spells.md`?
4. Inn-triggered shop restock — implement or drop from `shop.md`?
5. `world.yaml` overworld registry — create or drop from `map.md` / `transportation.md`?
