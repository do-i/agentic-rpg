# 12. Flag System

## Who Sets Flags

| Source | Example |
|---|---|
| Dialogue `on_complete` | `set_flag: boss_dragon_defeated` |
| Battle `on_complete` | `set_flag: boss_dragon_defeated` |
| Story script (cutscene) | `set_flag: story_act2_started` |
| System (new game bootstrap) | `set_flag: story_quest_started` |

## Lifecycle Rules

- **Boolean only** — presence = `true`, absence = `false`
- **Never cleared** — once set, permanent (V1)
- **No central registry** — scenario author owns all flag IDs
- **Uniqueness** — flag IDs must be unique across the entire scenario manifest
- **Evaluated at read time** — no pub/sub, no event bus; systems check flags on demand


## Schema

```yaml
# save state
flags:
  - story_quest_started
  - boss_dragon_defeated
  - npc_elder_reward_given
```

## Flag Consumers

| System | How it uses flags |
|---|---|
| Dialogue | `requires` / `excludes` conditions |
| Shop | `unlock_flag` gates item visibility |
| Apothecary | `unlock` gates recipe visibility |
| Battle | `once: true` prevents re-trigger |
| Map/Building | `flag` gates area/building access |
| Transportation | `unlock_flag` gates sail/fly/warp |
| NPC behavior | `condition` drives hint text |


## Bootstrap (New Game)

```yaml
# game bootstrap — injected once at new game start
flags:
  - story_quest_started
```

Single source of truth — all other systems use this as the default fallback condition.


## Naming Convention

`category_subject_state`

| Prefix | Example |
|---|---|
| `story_` | `story_act2_started` |
| `boss_` | `boss_dragon_defeated` |
| `npc_` | `npc_elder_reward_given` |
| `shop_` | `shop_blacksmith_unlocked` |
| `recipe_` | `recipe_hi_potion_unlocked` |
| `area_` | `area_cave_explored` |
| `transport_` | `transport_sail_unlocked` |
