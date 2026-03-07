# 13. Dialogue

## Core Model (Example)
- NPC monologue only — no player choices
- Condition: top-to-bottom, first match wins
- Re-evaluated every time player talks to NPC (dynamic)

### Dialogue Entry Schema

```yaml
# dialogue/elder_intro.yaml
id: elder_intro
entries:
  - condition:
      requires: [boss_dragon_defeated]
      excludes: [npc_elder_reward_given]
    lines:
      - "The dragon is gone. Peace has returned."
      - "Thank you, hero."
    on_complete:
      set_flag:
        - npc_elder_post_dragon_spoken
        - npc_elder_reward_given
      give_items:
        - id: elixir
          qty: 1
        - id: potion
          qty: 3

  - condition:
      requires: [story_act2_started]
      excludes: []
    lines:
      - "The cave to the north grows restless."
      - "Be careful out there."
    on_complete:
      unlock: shop_blacksmith_unlocked

  - condition:
      requires: [story_quest_started] # default fallback
      excludes: []
    lines:
      - "Welcome to our village, traveler."
    on_complete:
      start_battle: tutorial_slime    # optional — rare for NPC, but valid
```
### `on_complete` Actions

| Action | Effect |
|---|---|
| `set_flag` | Sets a flag in save state |
| `give_item` | Adds item(s) to Party Repository |
| `unlock` | Sets a shop/area unlock flag |
| `start_battle` | Triggers a scripted battle immediately after dialogue |

- All actions are **optional**
- Multiple actions allowed per entry — list them
- Actions fire **once per dialogue play-through**, not once-ever (re-evaluate = re-triggerable)

> ⚠️ **Design note:** If `give_item` re-triggers on every talk, player could farm it. Recommend pairing with `set_flag` + using that flag as a condition guard:

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
