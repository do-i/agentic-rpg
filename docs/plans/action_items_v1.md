# Action Items — v1

Self-contained tasks that should land before v1 ships. Done items are
deleted outright; only open work remains.

Status legend: 🟥 not started · 🟨 in progress · ❓ decision needed

---

## 1. Spot checks

Verification passes against the codebase. Each resolves to either
"confirmed, delete this line" or "found a gap, file a fix."

- 🟥 Build item shop sell UI (bag.md). `RepositoryState.sell_item`
  exists but no UI calls it; bag.md spec says sell list filters by
  tag and hides locked items.

---

## 2. Code review follow-ups

### 2.1 Trivial cleanups (can land any time)


### 2.3 Larger refactors still on the plan ❓

- §4.3 — `battle_renderer` panel split
- §4.4 — equip/spell wizard base class
- §4.5 — `action_resolver` split
- §3.5 — `SfxManager` null-object

❓ **Q3.** Which of these block v1?
- (a) All four — land before shipping.
- (b) None — defer all to post-v1.
- (c) Only one or two (specify which).

Answer: a

---

## 3. Scenario / asset work

### 3.1 Maps ❓

Need more TMX map files for v1.

❓ **Q4.** What's the v1 map target?
- (a) Just the existing `sample_dungeon_01` plus an overworld.
- (b) Overworld + 2-3 dungeons + 1-2 towns.
- (c) Full Act 1 coverage (specify regions).
- (d) You'll author them; I just stand by.

Answer: full @docs/scenario/high-level.md

### 3.2 Tile attribution ❓

Tag each tile with hints for AI-agent navigation.

❓ **Q5.** What attribution scheme?
- (a) Per-tile properties in the `.tsx` file (e.g. `walkable`,
  `terrain_type`, `cover`).
- (b) Sidecar YAML keyed by tile GID.
- (c) Custom Tiled object layer with semantic regions.
- (d) Defer until the AI-agent feature is scoped.

Answer:

### 3.3 SKILLs prompt update 🟥

Update the SKILLs prompt to enforce: *"no hardcoded method-param
defaults; if a YAML value is missing, raise with file name, property
name, and an example."*

(This is already in your auto-memory as a feedback rule — extending it
to SKILLs prompts is straightforward.)

❓ **Q6.** Which SKILLs need updating?
- (a) All scaffolding skills (`scaffold-content`, `new-scene`).
- (b) Only `scaffold-content`.
- (c) Point me at a specific skill file.

Answer:

### 3.4 `unlock_flag` chain wiring ❓

Wire `story_quest_started` → `story_act2_started` → ... from real NPC
dialogue / encounter triggers so the apothecary recipe unlock chain
fires at the right story beats.

❓ **Q7.** Scope for v1?
- (a) Wire the full chain end-to-end through Act 1.
- (b) Just the apothecary unlock — leave later acts as TODO.
- (c) Stub flags only; defer narrative wiring post-v1.

Answer:
