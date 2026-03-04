# 12. Flag System

## Schema

```
# in save file
flags:
  - boss_dragon_defeated
  - shop_blacksmith_unlocked
  - story_act2_started
```

## Naming Convention

`category_subject_state`

### Category examples

| prefix | flag name |
|---|---|
| `boss_` | `boss_dragon_defeated` |
| `shop_` | `shop_blacksmith_unlocked` |
| `story_` | `story_act2_started` |
| `npc_` | `npc_elder_spoken` |
| `recipe_` | `recipe_hi_potion_unlocked` |
| `area_` | `area_cave_explored` |

## Rules
- Boolean only — presence = `true`, absence = `false`
- Never reset in V1
- Plugin author defines all flag IDs — no central registry needed
- Flag IDs must be unique across the plugin manifest
