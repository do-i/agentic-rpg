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

The manifest declares two flag lists:

```yaml
# manifest.yaml
bootstrap_flags:           # injected once at New Game
  - story_quest_started

engine_managed_flags:      # the engine itself fires these at story milestones
  - story_act2_started
  - story_act3_started
  - story_act4_started
  - boss_zone10_defeated
```

`bootstrap_flags` are written into save state at New Game and act as the
default condition for any system that wants to gate by "the player has
started the game."

`engine_managed_flags` are story-milestone flags whose timing is part of
the scenario's narrative contract (act transitions, end-game). They MAY
be set from dialogue / encounter `on_complete` at the chosen story beat;
listing them here lets the validator treat them as "defined" so the
recipe / dialogue gating that consumes them passes audit even when the
specific trigger has not been wired yet.

For Rusted Kingdoms the act transitions fire from these dialogue beats:

| Flag | Trigger |
|---|---|
| `story_act2_started` | Elder reward in Ardel (after `boss_zone01_defeated`) |
| `story_act3_started` | Millhaven elder hint (after `boss_zone02_defeated`) |
| `story_act4_started` | Frostholm captain hint (after `boss_zone05_defeated`) |


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
