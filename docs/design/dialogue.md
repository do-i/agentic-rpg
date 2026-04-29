# 13. Dialogue

## Dialogue Types
```yaml
type: npc       # default — condition-driven, attached to NPC
type: cutscene  # one-shot — no conditions, no NPC, plays once
```

## Core Model (Example)
- NPC monologue only — no player choices
- Condition: top-to-bottom, first match wins
- Re-evaluated every time player talks to NPC (dynamic)

## Design summary

Dialogue entry ordering: bottom-up story progression — latest state first, default last.
excludes on give_items entries: always keep as safety net against re-triggering rewards.

### Dialogue Entry Schema

See `rusted_kingdoms/data/dialogue`

### `on_complete` Actions

| Action | Effect | Available in |
|---|---|---|
| `set_flag` | Sets a flag in save state | `npc`, `cutscene` |
| `give_items` | Adds item(s) to Party Repository | `npc`, `cutscene` |
| `unlock` | Sets a shop/area unlock flag | `npc`, `cutscene` |
| `start_battle` | Triggers a scripted battle immediately after dialogue | `npc` only |
| `join_party` | Adds a character to the active party | `npc`, `cutscene` |
| `transition` | Fades out and loads a new map at a given position | `cutscene` only |

- All actions are **optional**
- Multiple actions allowed per entry — list them
- Actions fire **once per dialogue play-through**, not once-ever (re-evaluate = re-triggerable)

> ⚠️ **Design note:** If `give_item` re-triggers on every talk, player could farm it. Recommend pairing with `set_flag` + using that flag as a condition guard:

## `transition` schema

```yaml
on_complete:
  transition:
    map: town_01_ardel      # map id to load
    position: [12, 8]       # spawn position
    fade: in                # fade direction after load: in | out | none
```
## Cutscene schema (full example)

```yaml
id: intro_cutscene
type: cutscene

lines:
  - "Long ago, a flame fell from the sky..."
  - "..."

on_complete:
  transition:
    map: town_01_ardel
    position: [12, 8]
    fade: in
```

## Engine behaviour rules

- `type: cutscene` — no condition evaluation, no NPC lookup, plays top to bottom once
- `transition` fires **after** all lines complete and screen fades out
- `start_battle` blocked in cutscene context — use map encounter config instead

## Condition Evaluation (Pseudocode)

```python
for entry in entries:
    if all(requires flags present) and none(excludes flags present):
        play entry
        break
```

## Evaluation Flow
```
Player talks to NPC
  → Load dialogue file by NPC id
  → Walk entries top to bottom
  → First entry where condition = true → play lines
  → Fire on_complete actions
  → Done
```

## NPC Map Config Hook

# map/town_01.yaml

```yaml
npcs:
  - id: elder
    dialogue: elder_intro
    position: [12, 8]
```

## Init Flag
```yaml
# game bootstrap — always injected at new game start
flags:
  - story_quest_started
```

### Benefits
- `story_quest_started` is a real flag — can be consumed by other systems too
- Evaluation stays uniform: top-to-bottom, first match wins
- Scenario author can use `story_quest_started` as baseline condition anywhere
