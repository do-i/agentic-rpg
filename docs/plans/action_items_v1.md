# Action Items — v1

Self-contained tasks that should land before v1 ships. Done items are
deleted outright; only open work remains.

Status legend: 🟥 not started · 🟨 in progress · ❓ decision needed

---

## 1. Spot checks

Verification passes against the codebase. Each resolves to either
"confirmed, delete this line" or "found a gap, file a fix."

- 🟥 Enemy targeting overrides (`random_alive`, `lowest_hp`,
  `all_party`) all covered in `battle_enemy_logic.py` (enemy.md).
- 🟥 `NpcLoader` honors `present.requires/excludes` (map.md).
- 🟥 `NpcLoader` reads `animation: { mode, speed, range }` (npc.md).
- 🟥 Item shop sell flow filters by tag (bag.md).
- 🟥 Phoenix-Down-equivalent KO-revive item exists in
  `consumables_recovery.yaml` (party.md).

❓ **Q1.** Run all spot checks now in one pass, or wait until you flag a
specific one?
- (a) Run all now and report findings.
- (b) Wait — you'll point at one when relevant.
- (c) Run as a background agent task.

Answer: a

---

## 2. Code review follow-ups

### 2.1 Trivial cleanups (can land any time)

- 🟥 `RepositoryState.add_gp` returns `int` but call sites discard it
  (`engine/party/repository_state.py:66`).
- 🟥 `engine/world/world_map_renderer.py:99-104` — `_fade_surf` refilled
  every frame; revisit on a profiler pass.
- 🟥 `engine/world/world_map_scene.py:415-426` — `update()` runs
  `_engaged_enemy` deactivation before fade/overlay checks; reorder is
  cosmetic.
- 🟥 `engine/io/save_manager.py` missing `from __future__ import
  annotations` (relies on PEP 649 pinned by `pyproject.toml >=3.14.3`).

### 2.2 pygame / Python 3.14 wheel gap ❓

`pygame==2.6.1` has no Python 3.14 wheels, so CI cannot install on the
declared Python version.

❓ **Q2.** How do you want to resolve this?
- (a) Downgrade `pyproject.toml` Python pin to 3.13 (drop PEP 649
  reliance — re-add `from __future__ import annotations` where needed).
- (b) Switch to `pygame-ce` (community edition usually has earlier
  wheel releases for new Python versions).
- (c) Wait for upstream `pygame` 3.14 wheels; mark CI Python as 3.13
  for now while leaving runtime declaration at 3.14.
- (d) Build pygame from source in CI.

Answer:

### 2.3 Larger refactors still on the plan ❓

- §4.3 — `battle_renderer` panel split
- §4.4 — equip/spell wizard base class
- §4.5 — `action_resolver` split
- §3.5 — `SfxManager` null-object

❓ **Q3.** Which of these block v1?
- (a) All four — land before shipping.
- (b) None — defer all to post-v1.
- (c) Only one or two (specify which).

Answer:

---

## 3. Scenario / asset work

### 3.1 Maps ❓

Need more TMX map files for v1.

❓ **Q4.** What's the v1 map target?
- (a) Just the existing `sample_dungeon_01` plus an overworld.
- (b) Overworld + 2-3 dungeons + 1-2 towns.
- (c) Full Act 1 coverage (specify regions).
- (d) You'll author them; I just stand by.

Answer:

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
