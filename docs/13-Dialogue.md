# 13. Dialogue

## Core Model (Example)

```yaml
# dialogue/elder_intro.yaml
id: elder_intro
entries:
  - condition: boss_dragon_defeated
    lines:
      - "The dragon is gone. Peace has returned."
      - "Thank you, hero."
  - condition: story_act2_started
    lines:
      - "The cave to the north grows restless."
      - "Be careful out there."
  - condition: story_quest_started    # default fallback
    lines:
      - "Welcome to our village, traveler."
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
- Plugin author can use `story_quest_started` as baseline condition anywhere
