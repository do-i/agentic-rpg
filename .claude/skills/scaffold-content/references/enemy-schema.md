# Enemy Schema — Full Reference

Enemy documents live in `rusted_kingdoms/data/enemies/enemies_rank_<N>_<TIER>.yaml`.
Multiple enemies per file, each separated by `---`.

## Required Fields

```yaml
id: string           # unique, lowercase_with_underscores
name: string
type: string         # beast | demon | undead | construct | spirit | ...
rank: string         # SS | S | A | B | C | D | E | F
hp: int
atk: int
def: int
mres: int            # magic resistance
dex: int
exp: int
```

## Optional Fields

```yaml
boss: false          # true = boss-level; affects UI and music
sprite_scale: 100    # percent; default 100

immune_to:
  - instant_kill

barrier: false
requires_item: <item_id>   # item needed to pierce barrier
```

## Drops

```yaml
drops:
  mc:                # magic core drops
    - size: XS       # XS | S | M | L | XL
      qty: 1
  loot:
    - pool:
        - item: <item_id>
          weight: 10
```

## Inline AI (standard enemies)

```yaml
ai:
  pattern: random       # random | weighted
  moves:
    - action: attack
      weight: 10
    - action: ability
      id: <ability_id>
      weight: 5

targeting:
  default: random_alive  # random_alive | highest_dex | party_member | lowest_hp
  overrides:
    - ability: <ability_id>
      target: highest_dex
```

## External AI (boss enemies)

Instead of inline `ai:`, reference a boss move set file:

```yaml
ai_ref: data/enemies/boss_move_sets/<boss_id>_moves.yaml
```

Boss move set file format (`data/enemies/boss_move_sets/*.yaml`):

```yaml
ai:
  pattern: random
  moves:
    - action: attack
      weight: 8
    - action: ability
      id: fire_breath
      weight: 5
    - action: ability
      id: tail_swipe
      weight: 3

targeting:
  default: random_alive
  overrides:
    - ability: fire_breath
      target: all_party
```

## Complete Boss Example

```yaml
---
id: iron_colossus
name: Iron Colossus
type: construct
rank: SS
hp: 4800
atk: 220
def: 180
mres: 60
dex: 30
exp: 8000
boss: true
sprite_scale: 150
immune_to:
  - instant_kill
  - poison
barrier: false
drops:
  mc:
    - size: XL
      qty: 3
  loot:
    - pool:
        - item: core_iron_giant
          weight: 10
ai_ref: data/enemies/boss_move_sets/iron_colossus_moves.yaml
```
