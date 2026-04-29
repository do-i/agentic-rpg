# Action Items — v1

Self-contained tasks that should land before v1 ships. Doc-only fixes that
were already swept by the recent "reduce gaps b/w docs and implementation"
pass have been removed; only items requiring a code decision or fresh work
remain.

Status legend: 🟥 not started · 🟨 in progress · 🟩 done · ❓ decision needed

---

## Code decisions (need user input)

### 1. ❓ Tag-editing UI in item screen
`bag.md` specifies an `[Edit Tags]` panel (toggle system tags + custom-tag
creation). Repository data layer (`add_tag` / `remove_tag` / `set_locked` /
`max_tags=5` / `items_by_tag`) is implemented; only the UI flow is missing.
Decide: build the edit UI, or drop the spec from `bag.md`.

### 2. ❓ Ultimate-spell story-flag gate
`spells.md` says ultimates (lvl 46/48/50/52) are gated by a story flag;
class YAMLs only check `unlock_level`. Decide: add a flag-gate at spell
unlock, or drop the gate from `spells.md`.

### 3. ❓ Inn-triggered shop restock
`shop.md` claims "every rest triggers full restock"; `InnScene` does not
call into shop state. Decide: implement restock on rest, or drop the
restock semantics from `shop.md`.

### 4. ❓ Item filter tabs (All/Recovery/Status/Battle/Key)
`screen.md` specifies filter tabs in the item screen; current UI shows a
tag list but no tab filter. Decide: implement, or drop from `screen.md`.

### 5. ❓ Sell price = 0.5 × buy default rule
`equipment.md` claims `sell_price` is auto-derived as half of `buy_price`;
code stores `sell_price` explicitly per item. Decide: add the auto-derive
default, or drop the claim from `equipment.md`.

### 6. ❓ Party stats not yet implemented
`party.md` lists `encounter_modifier` and `trap_detect` (only `flee_rate`
ships). `taunt` / `def_up` appear in `party.md` but are not in the
`StatusEffect` enum (POISON/SLEEP/STUN/SILENCE/KNOCKBACK only). Decide
each: implement or drop from doc.

### 7. ❓ Dialogue `unlock` action
`dialogue.md` lists an `unlock` action under `on_complete`; dispatcher
does not implement it. Decide: implement, or drop from doc.

---

## Spot checks still pending (from `systems-gap-v1.md`)

These are quick verification passes; resolve with a one-line answer or a
small fix.

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

## Code review follow-ups (from `code-review.md`)

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

## Scenario / asset work (from `remaining-refactor.md`)

- Create more TMX map files.
- Attribute each tile (for AI agent navigation hints).
- Update SKILLs prompt: enforce "no hardcoded method-param defaults; if
  a YAML value is missing, raise with file name, property name, and an
  example."
- Scenario authoring (parallel track) — wire `unlock_flag` chain
  (`story_quest_started` → `story_act2_started` → ...) from real NPC
  dialogue / encounter triggers so the apothecary recipe unlock chain
  fires at the right story beats.
