# Validation strategy for data files

## Approach

Start from `manifest.yaml` as root, traverse all references depth-first, collect broken links and unreachable files.

## Two Passes

**Pass 1 — Forward traversal (broken links)**
Walk every known reference type and check the target exists.

**Pass 2 — Reverse coverage (unreachable entities)**
Compare all files on disk against everything visited in Pass 1. Anything not visited = unreachable.

## Reference Types to Traverse

| Source File | Field | Target |
|---|---|---|
| `manifest.yaml` | `character` | `data/characters/*.yaml` |
| `manifest.yaml` | `intro_dialogue` | `data/dialogue/*.yaml` |
| `map/*.yaml` | `npcs[].dialogue` | `data/dialogue/*.yaml` |
| `dialogue/*.yaml` | `on_complete.join_party` | `data/characters/*.yaml` |
| `encount/*.yaml` | `boss.on_complete.set_flag` | flag registry (collect only) |
| `dialogue/*.yaml` | `on_complete.set_flag` | flag registry (collect only) |
| `dialogue/*.yaml` | `requires` / `excludes` | flag registry (validate flags exist) |
| `recipe/*.yaml` | `inputs.items[].id` | `data/items/*.yaml` |
| `recipe/*.yaml` | `output.item` | `data/items/*.yaml` |
| `map/*.yaml` | `shop.items[].id` | `data/items/*.yaml` |
| `encount/*.yaml` | `entries[].formation[]` | `data/enemies/*.yaml` (enemy id) |
| `encount/*.yaml` | `boss.id` | `data/enemies/*.yaml` (boss enemy id) |
| `encount/*.yaml` | `barrier_enemies[].id` / `requires_item` | `data/enemies/`, `data/items/` |
| `enemies/*.yaml` | `drops.loot[].pool[].item` | `data/items/*.yaml` |
| `enemies/*.yaml` | `ai_ref` | `data/enemies/boss_move_sets/*.yaml` |
| `manifest.yaml` | `engine_managed_flags` | flag registry (collect only) |

## Output Format

```
BROKEN LINKS
  [dialogue] millhaven_elder_hint.yaml → requires flag: boss_zone99_defeated  (not defined anywhere)

UNREACHABLE FILES
  data/dialogue/old_draft.yaml  (never referenced)

FLAG AUDIT
  Defined: 24 flags
  Consumed: 22 flags
  Orphan flags (set but never consumed): boss_zone03_defeated
```

## One Design Decision

**Flag validation** — flags aren't files, they're strings scattered across yaml. The validator needs to:
1. Collect all `set_flag` occurrences → "defined" set
2. Collect all `requires`/`excludes` occurrences → "consumed" set
3. Report anything consumed but never defined (broken), and defined but never consumed (orphan)
