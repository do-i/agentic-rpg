# 3. Battle System

Turn-based, command-menu driven

**Command menu:** Attack / Spell / Item / Run

## Suggested Loading Strategy

Two-phase approach:

- **Phase 1 — startup:** Build `rank_index` (and optionally a `name_index`) from all enemy YAMLs. Lightweight scan, keyed by `id`.
- **Phase 2 — battle trigger:** Load only the specific enemy YAML docs needed for that formation. Targeted, not bulk.


```python
# At startup — build rank index from filenames + ids
rank_index = {}  # {enemy_id: rank}

for path in glob("data/enemies/enemies_rank_*.yaml"):
    for doc in yaml.safe_load_all(open(path)):
        rank_index[doc["id"]] = doc["rank"]

# Phase 2 — targeted load example
def load_enemy(enemy_id: str) -> dict:
    rank = rank_index[enemy_id]
    path = f"data/enemies/enemies_{rank}.yaml"
    for doc in yaml.safe_load_all(open(path)):
        if doc["id"] == enemy_id:
            return doc
```

The filename convention does double duty — `rank_index` tells you which file to open directly. No scanning other files at all.


## Combat Resolution & Damage Formula

```
# Turn order
order = dex descending; tie → party wins

# Hit or Miss
hit_chance = clamp(0.70 + (attacker_dex - defender_dex) * 0.02, 0.05, 0.95)

# Physical
damage = max(1, (str + weapon_atk) - enemy_def)

# Crit (physical only)
crit_chance = min(dex * 0.02, 0.25)
crit_damage = damage * 1.5

# Spell
damage = max(1, (int * spell_coeff) - enemy_mres)
# Note: spell_coeff see character-class-config

# Heal
amount = int * heal_coeff
# Note: heal_coeff see character-class-config
```
## Hit Chance

| attacker_dex - defender_dex | hit_chance |
|---|---|
| +70 | 0.95 (Ceiling)|
| +10 | 0.90 |
| 0 (equal) | 0.70 |
| -10 | 0.50 |
| -20 | 0.30 |
| -80 | 0.05 (floor)|


## Resolution Order

1. Compute hit_chance
2. Roll hit → miss: show "MISS", end
3. Compute base damage
4. Roll crit → apply ×1.5 if triggered
5. Apply final damage

## Status Effect Interactions


| Effect | Damage | Timing | Duration | Stack |
|---|---|---|---|---|
| `poison` | `max(1, floor(enemy_atk * 0.10))` | End of turn | until cured | reset on re-apply |
| `sleep` | — | — | until hit | reset on re-apply |
| `stun` | — | — | 1 turn | no |
| `silence` | — | — | until cured | reset on re-apply |

Good addition. Cure sources — locked:

### Cure Matrix

| Effect | Cleric: Cure | Item | Rest in bed / tent |
|---|---|---|---|
| `poison` | ✅ | ✅ | ✅ |
| `sleep` | — | ✅ | — |
| `stun` | — | — | — |
| `silence` | ✅ | ✅ | ✅ |

**Note:** Bed/tent also implies full HP/MP restore — needs to be defined when we cover the **Map/Town rest system**. Flagging that as a design item.

## Encounter System

Encounters are **tile-spawner driven**, not D100-per-step. Each dungeon zone
has a population of enemy sprites placed on walkable tiles; collision triggers
the battle. There is no global "encounter rate" probability per step.

### Per-zone tuning (`encount/*.yaml`)

```yaml
id: zone_01_starting_forest
name: Starting Forest
density: 0.70             # share of walkable tiles eligible for spawns
spawn_frequency: 25.0     # respawn cadence after a battle
background: world1-bg-1280x468

entries:
  - formation: [goblin]
    weight: 25
    chase_range: 8        # tiles — how far the sprite chases the player
  - formation: [goblin, goblin, goblin]
    weight: 25
    chase_range: 6

boss:
  id: grik_the_grin_192
  name: Grik the Grin
  once: true
  on_complete:
    set_flag: boss_zone01_defeated

barrier_enemies:          # optional — present-check items, not consumed
  - id: ghost
    requires_item: veil_breaker
    blocked_message: "A mysterious force blocks your attack."
```

### Stealth-Cloak Effect

The `stealth_cloak` accessory **reduces enemy chase range** rather than
modifying a global encounter probability. Tunable via `balance.yaml`
(`spawner.stealth_cloak_reduction`).

### Formation Roll

When the player collides with a spawn:

```
Roll D100 against entries[].weight (walked cumulatively)
→ formation selected
```

Boss encounters are scripted (`once: true`) and bypass the spawner population.

## Encounter Group

Enemy formation min: 1; max: 5
weight total must always be 100.

```yaml
id: forest_enemies
entries:
  - formation: [forest_wolf]
    weight: 40
  - formation: [forest_wolf, forest_wolf]
    weight: 30
  - formation: [forest_wolf, forest_wolf, forest_wolf]
    weight: 25
  - formation: [forest_wolf, cave_bat]
    weight: 5
  - formation: [forest_wolf, forest_wolf, cave_bat, cave_bat]
```

## Battle Damage Formula

Spells/abilities ignore row entirely (only physical is affected)

**Incoming physical damage to party member:**
```
incoming_physical = max(1, (enemy_atk) - member_def)

if member.row == back:
    incoming_physical = floor(incoming_physical * 0.5)
```

**Outgoing physical damage from back row:**
```
if attacker.row == back AND ability.attack_range == melee:
    damage = floor(damage * 0.5)   # penalty for melee from back
elif attacker.row == back AND ability.attack_range == ranged:
    damage = damage                # no penalty
```

Spells (`type: spell`, `type: heal`) → **row ignored entirely**.


### Summary Table

| Attacker Row | Attack Type | Damage |
|---|---|---|
| Front | Melee | Full |
| Back | Melee | ×0.5 |
| Back | Ranged | Full |
| Any | Spell | Full (row ignored) |
| Front/Back | Incoming physical | Full / ×0.5 |

### Row Assignment

| Member | Default Row |
|---|---|
| Hero | Front |
| Warrior | Front |
| Sorcerer | Back |
| Cleric | Back |
| Rogue | Back (default) |

Player can swap Rogue to Front via party arrangement screen.

### Ability Schema Addition

```yaml
# example: rogue back-row melee vs ranged
- id: dual_strike
  attack_range: melee    # penalized from back row

- id: steal
  attack_range: melee

- id: shadow_step
  attack_range: melee    # vanish mechanic — could exempt this one
```

Default: if `attack_range` omitted → assume `melee`.

## Post-Battle Rewards

| Reward | Rule |
|---|---|
| **EXP** | Always; split equally among living members |
| **Magic Core (MC)** | Always; minimum 1 guaranteed |
| **Items** | Random chance; 0 or more |

## Game Over & Retry

**Flow**
```
All members HP = 0
  → Game Over screen
    ├── Resume from last autosave
    ├── Resume from any manual save slot
    └── Quit
```

## No Penalty
GP, items, flags all restored to save state
Nothing is lost beyond progress since last save

## Save State Restored

- character status (hp, mp, status effects)
- party repository (items, gp)
- flags
- map location

