# Action Items — v1

Self-contained tasks that should land before v1 ships. Done items are
deleted outright; only open work remains.

Status legend: 🟥 not started · 🟨 in progress · ❓ decision needed

---

## Code decisions (need user input)

### 1. ❓ Tag-editing UI in item screen
`bag.md` specifies an `[Edit Tags]` panel (toggle system tags + custom-tag
creation). Repository data layer (`add_tag` / `remove_tag` / `set_locked` /
`max_tags=5` / `items_by_tag`) is implemented; only the UI flow is missing.

- A. Build the edit UI as `bag.md` specifies.
- B. Drop the spec from `bag.md` and keep tags author-only.
- C. Other.

**Answer:**

### 2. ❓ Ultimate-spell story-flag gate
`spells.md` says ultimates (lvl 46/48/50/52) are gated by a story flag;
class YAMLs only check `unlock_level`.

- A. Add a flag-gate at spell unlock (extend resolver + class YAML).
- B. Drop the gate from `spells.md`; level alone unlocks.
- C. Other.

**Answer:**

### 3. ❓ Inn-triggered shop restock
`shop.md` claims "every rest triggers full restock"; `InnScene` does not
call into shop state.

- A. Implement restock-on-rest in `InnScene`.
- B. Drop the restock semantics from `shop.md` (stock is static).
- C. Other.

**Answer:**

### 4. ❓ Item filter tabs (All/Recovery/Status/Battle/Key)
`screen.md` specifies filter tabs in the item screen; current UI shows a
tag list but no tab filter.

- A. Implement the tab filter in `item_renderer.py`.
- B. Drop from `screen.md`; current tag list is enough.
- C. Other.

**Answer:**

### 5. ❓ Sell price = 0.5 × buy default rule
`equipment.md` claims `sell_price` is auto-derived as half of `buy_price`;
code stores `sell_price` explicitly per item.

- A. Add the auto-derive default; allow per-item override.
- B. Drop the claim from `equipment.md`; require explicit `sell_price`.
- C. Other.

**Answer:**

### 6. ❓ Party stats not yet implemented
`party.md` lists `encounter_modifier` and `trap_detect` (only `flee_rate`
ships). It also lists `taunt` / `def_up` statuses, which are not in the
`StatusEffect` enum (POISON/SLEEP/STUN/SILENCE/KNOCKBACK only).

- A. Implement all four (`encounter_modifier`, `trap_detect`, `taunt`,
  `def_up`).
- B. Implement only `encounter_modifier` + `trap_detect`; drop the two
  statuses from `party.md`.
- C. Drop all four from `party.md`.
- D. Other.

**Answer:**

### 7. ❓ Dialogue `unlock` action
`dialogue.md` lists an `unlock` action under `on_complete`; dispatcher
does not implement it.

- A. Implement `unlock` (e.g. unlock a recipe / spell / location).
- B. Drop it from `dialogue.md`.
- C. Other.

**Answer:**

---

## Spot checks still pending

Quick verification passes; resolve with a one-line answer or a small fix.

- `InnScene` clears statuses on rest (battle.md status cure matrix).
- `boss_move_sets/<id>.yaml` resolves through enemy loader (enemy.md).
- `BarrierEnemy.requires_item` is wired to item present-check, not
  consumption (enemy.md).
- Enemy targeting overrides (`random_alive`, `lowest_hp`, `all_party`) all
  covered in `battle_enemy_logic.py` (enemy.md).
- `NpcLoader` honors `present.requires/excludes` (map.md).
- `NpcLoader` reads `animation: { mode, speed, range }` (npc.md).
- Item shop sell flow filters by tag (bag.md).
- Phoenix-Down equivalent KO-revive item exists in
  `consumables_recovery.yaml` (party.md).

---

## Code review follow-ups

Small, deferrable cleanups — pick up opportunistically.

- `RepositoryState.add_gp` returns `int` but call sites treat it as
  `None` (`engine/party/repository_state.py:66`). Harmless until a
  type-checker is wired in.
- `engine/world/world_map_renderer.py:99-104` — `_fade_surf` reused but
  refilled every frame; revisit during a profiler pass.
- `engine/world/world_map_scene.py:415-426` — `update()` runs
  `_engaged_enemy` deactivation before fade/overlay checks; reordering
  is cosmetic.
- `engine/io/save_manager.py` lacks `from __future__ import
  annotations`; relies on PEP 649 deferred eval pinned by
  `pyproject.toml >=3.14.3`.
- pygame pin: `pygame==2.6.1` lacks Python 3.14 wheels; CI on the
  declared Python version cannot install.
- Larger refactors still on the plan: §4.3 (battle_renderer panel
  split), §4.4 (equip/spell wizard base), §4.5 (action_resolver split),
  §3.5 (`SfxManager` null-object).

---

## Scenario / asset work

- Create more TMX map files.
- Attribute each tile (for AI agent navigation hints).
- Update SKILLs prompt: enforce "no hardcoded method-param defaults; if
  a YAML value is missing, raise with file name, property name, and an
  example."
- Scenario authoring (parallel track) — wire `unlock_flag` chain
  (`story_quest_started` → `story_act2_started` → ...) from real NPC
  dialogue / encounter triggers so the apothecary recipe unlock chain
  fires at the right story beats.
