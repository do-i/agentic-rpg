# Action Items — Code Changes from `systems-gap-v1.md`

Each task is **self-contained**: it carries enough context to be picked up in
a fresh session without re-reading the gap analysis. Doc-only fixes from
`systems-gap-v1.md` have already been applied; this file tracks **code
changes only**.

Status legend: 🟥 not started · 🟨 in progress · 🟩 done · ❓ decision needed

---

## 1. 🟩 Implement front/back row + `attack_range` ability flag

**Why**
`docs/design/battle.md` and `docs/design/party.md` specify a row system:
front-row members take full physical damage and deal full melee damage; back
row takes ×0.5 incoming physical and deals ×0.5 outgoing melee (ranged and
spell ignore the penalty). The code currently has **no row state and no
`attack_range` field on abilities** — every party member is implicitly
front-row.

**Scope**
1. Add `row: "front" | "back"` to `engine/party/member_state.py` (default
   per class — Hero/Warrior front, Sorcerer/Cleric/Rogue back; Rogue is
   user-swappable per `party.md`). Persist in save (`save.md` schema, see
   `engine/io/save_manager.py::_serialize`).
2. Mirror onto `engine/battle/combatant.py::Combatant` so battle code can
   read it without touching `MemberState` directly.
3. Read optional `attack_range: melee | ranged` from class-ability YAML in
   `engine/party/party_state.py` ability loader; default `melee`.
4. Apply the row math in `engine/battle/action_resolver.py`:
   - Incoming physical to back-row member → `floor(dmg * 0.5)`.
   - Outgoing melee from back-row attacker → `floor(dmg * 0.5)`.
   - Outgoing ranged or `type: spell|heal` → unaffected.
5. Add a UI affordance to swap Rogue front/back (likely in
   `engine/status/status_scene.py` or a new submenu); pure data toggle.
6. Tests in `tests/unit/battle/` for the four cases in `battle.md`'s summary
   table.

**Files**
- `engine/party/member_state.py`
- `engine/party/party_state.py`
- `engine/battle/combatant.py`
- `engine/battle/action_resolver.py`
- `engine/io/save_manager.py` (+ loader in `engine/io/game_state_loader.py`)
- `rusted_kingdoms/data/classes/*.yaml` — add `attack_range` where it
  matters (e.g. Rogue `dual_strike` melee, ranged abilities)
- `tests/unit/battle/test_action_resolver.py` (new cases)

**Acceptance**
- Back-row member takes half physical damage from a basic attack.
- Back-row Rogue using a `melee` ability deals half damage; using a
  `ranged` ability deals full.
- Spell/heal damage unaffected by row.
- Save/load round-trips `row` per member.

---

## 2. ❓ Tag-editing UI in Item screen

**Status**: decision needed — implement or drop the spec from `bag.md`.

**Why**
`docs/design/bag.md` specifies an "Edit Tags" panel reachable from item
detail, with system-tag toggles + custom-tag creation (max 5 tags per
item). The data layer (`RepositoryState.add_tag`, `remove_tag`,
`set_locked`, `max_tags_per_item`) is fully implemented; only the UI is
missing.

**If implementing — scope**
1. Add an "Edit Tags" sub-state to `engine/item/item_scene.py` reached
   from the item detail panel (new key handler).
2. Render checkbox-style toggle list of system tags + a "+New Tag…" row
   that opens a small text-entry overlay (reuse `engine/title/name_entry_scene.py`
   pattern, but as an inline modal).
3. Enforce the 5-tag cap (already enforced in `RepositoryState.add_tag` —
   show "max tags reached" toast).
4. Verify sell-by-tag filter is reachable in `engine/shop/item_shop_scene.py`
   (`bag.md` mentions "Sell all [consumable]"). If missing, add it.

**Decision**
The data API is already shipped, so if this is judged out-of-scope for V1
gameplay, **drop the UI section from `bag.md`** instead. Flag for user
input.

---

## 3. ❓ Story-flag gate on ultimate spells

**Status**: decision needed.

**Why**
`docs/design/spells.md` says "ultimates gated by story flag" (the lvl
46/48/50/52 + flag tier — Meteor, Absolute Zero, Tornado, Terra Break).
Class YAMLs (`rusted_kingdoms/data/classes/sorcerer.yaml`,
`cleric.yaml`) only carry `unlock_level`; there is no flag check on
ability unlock anywhere in code.

**If implementing — scope**
1. Optional `unlock_flag: <flag_id>` on ability entries in class YAMLs.
2. In `engine/party/party_state.py` (or wherever abilities are filtered
   for "currently usable"), require the flag to be set in addition to
   `unlock_level`.
3. Decide which flag gates which ultimate (likely
   `story_act4_started` or a dedicated `spell_meteor_unlocked` line).
4. Update `data/classes/sorcerer.yaml` etc. with `unlock_flag` on the
   four ultimates.
5. Tests: ability list excludes the spell at level 50 without the flag,
   includes it once the flag is set.

**Decision**
If we don't want this complexity, drop the line from `spells.md`. Flag
for user input.

---

## 4. ❓ Inn-triggered shop restock

**Status**: decision needed.

**Why**
`docs/design/shop.md` says "Every rest (inn or Rest Capsule) triggers
full restock across all shops." Verify that `engine/inn/inn_scene.py`
calls into shop state to reset stock; if not, either implement it or
drop the line from the doc. Current shop state lives implicitly in the
map YAML (`shop.items[].qty`) and may already be effectively stateless
(qty is the *cap*, not a depleting counter).

**Investigation steps for the next session**
1. Read `engine/inn/inn_scene.py`, `engine/shop/item_shop_scene.py`,
   `engine/shop/magic_core_shop_scene.py` to see whether shop stock is
   ever actually consumed.
2. If shop stock does not deplete (the YAML qty is the per-visit cap),
   the doc claim is vacuous — **drop it from `shop.md`**.
3. If stock depletes across visits, implement a `restock_all_shops()`
   call from `InnScene` on rest-confirm.

**Decision**
Likely **doc drop** is correct; confirm by inspection, then either
update doc or implement.


---

## 5. 🟩 Spot-check pass: verify "verify in code" claims

| # | Claim | Result |
|---|---|---|
| 1 | `InnScene` clears status effects on rest (`battle.md` cure matrix) | ✅ vacuous — `MemberState` has no `status_effects`; status lives only on `Combatant` during battle and never persists. Nothing to clear at rest. (Doc claim is moot under current architecture.) |
| 2 | `NpcLoader` honors `present.requires` / `excludes` | ✅ `npc_loader.py:51,68-69` reads them; `Npc.is_present(flags)` checks via `FlagState.has_all`/`has_none`; consumed in `world_map_scene.py:155` and `world_map_logic.py:48`. |
| 3 | `BarrierEnemy.requires_item` is a presence-check, not consumed | ✅ `encounter_resolver.py:89` uses `not in inventory_item_ids`. |
| 4 | `heal_pct` ability field is honored (Hero `second_wind`) | 🟩 fixed in this pass — `action_resolver.py` heal branch was ignoring `heal_pct`; now `heal_pct` (target.hp_max%) takes precedence over `heal_coeff` (mres-scaled). Test added: `test_battle_logic.py::test_heal_spell_with_heal_pct_uses_target_hp_max`. |
| 5 | `Phoenix Down` (revive item) exists | ✅ no literal "Phoenix Down", but `Life Crystal` (revive 1.0) and `Phoenix Wing` (revive 0.30) cover the slot. |
| 6 | No-drop loot semantics | ⚠ doc-imprecise. `weighted_pick` uses `rng.choices` (normalized weights) — short-sum does NOT give a no-drop chance. No-drop is reachable via an explicit `item: ""` row (skipped at `battle_rewards.py:187`). All 76 current loot pools sum ≥100 with no empty-item rows, so the question is academic for V1. **Doc fix: drop the "weights summing < 100" line wherever it appears; the actual mechanism is empty-item entries.** |
| 7 | `tools/validate.py` traverses recipe inputs/outputs | ✅ `validate.py:358-376`. |
| 8 | Boss `ai_ref: boss_move_sets/<id>.yaml` is loaded | ✅ `enemy_loader.py:93-111`; 10 boss AI files exist under `data/enemies/boss_move_sets/`. |
| 9 | Enemy targeting overrides (`lowest_hp`, `all_party`) | ✅ `battle_enemy_logic.py:152-161` implements `all_party`, `self`, `lowest_hp`, `highest_hp`, `random_alive`, with per-ability override at `:143-146`. |
| 10 | Item filter tabs (All/Recovery/Status/Battle/Key) | ✅ `item_logic.py:14`: `TABS = ["New", "All", "Recovery", "Status", "Battle", "Material", "Magic Core", "Key"]` — exceeds doc spec. |

All ten checks resolved in this pass. Doc fix for row 6 applied to
`docs/design/loot.md` (no-drop = explicit `item: ""` row, not weight
shortfall). Code fix for row 4 (`heal_pct`) committed with this
update.

---

## 6. 🟥 (v2, deferred) Transportation system

Already tracked in `docs/plans/systems-gap.md`. Summary: no transport
scene, no `port_tiles`, `MapState.visited` collected but never read.
Out of scope for V1; do not start until V1 scenario is fully playable.

---

## Index of Doc-Only Fixes (already applied)

For traceability — these were committed as part of the same gap-analysis
follow-up and do not need re-doing:

- `docs/design/architecture.md` — corrected tech stack (Python 3.14, vanilla
  Pygame, setuptools, no scripting sandbox).
- `docs/design/save.md` — corrected filename format (`{slot:03d}.yaml`),
  added `exp_next` / `opened_boxes`, documented why `abilities_unlocked`
  and `status_effects` are not persisted.
- `docs/design/scenario.md` — expanded manifest schema (title, font,
  apothecary/inn/item_shop/item_box, `bootstrap_flags`,
  `engine_managed_flags`, `refs`).
- `docs/design/validation.md` — extended reference table to include
  encounter/enemy/manifest references.
- `docs/design/battle.md` — replaced `encounter_rate` formula section
  with the actual tile-spawner / `density` / `chase_range` model.
- `docs/design/enemy.md` — removed stale zone roster tables (point to
  YAML), dropped `mc_tier`, replaced reward-stat schema.
- `docs/design/dialogue.md` — corrected `on_complete` action table
  (added `open_shop` / `open_inn` / `open_apothecary`, removed
  unimplemented `unlock`).
- `docs/design/map.md` — removed `world.yaml` reference.
- `docs/design/apothecally.md` — flat `unlock_flag`, documented
  `unique_output`, removed `phoenix_wing` speculation.
- `docs/design/equipment.md` — corrected field name (`equippable`),
  noted `sell_price` is explicit (not auto-derived).
- `docs/design/flag.md` — documented `bootstrap_flags` and
  `engine_managed_flags`.
- `CLAUDE.md` — updated package layout (no `dto/` / `service/` / `ui/`).
