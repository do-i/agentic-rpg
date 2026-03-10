# 3. Battle System

Turn-based, command-menu driven

**Command menu:** Attack / Spell / Item / Run

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

## Encounter Rate System

### Base Formula

```
final_encounter_rate = clamp(encounter_rate + encounter_modifier, 0.0, 1.0)
```
- `encounter_rate` — defined per map in scenario config
- `encounter_modifier` — sum of all equipped accessory modifiers on Rogue only
- Any party position works


### Accessory Schema

```yaml
# items/stealth_cloak.yaml
id: stealth_cloak
type: accessory
gp_cost: 800
equippable: [rogue]
stats:
  encounter_modifier: -0.15    # reduce encounters

# items/lure_charm.yaml
id: lure_charm
type: accessory
gp_cost: 600
equippable: [rogue]
stats:
  encounter_modifier: +0.20    # increase encounters (grinding)
```

### Why Both Directions

| Direction | Use Case |
|---|---|
| `-` reduce | Stealth run, low-resource, story focus |
| `+` increase | Grinding EXP/GP, farming loot |

### Map Config

```yaml
# maps/forest.yaml
encounter_rate: 0.15    # base — before modifier
```

### Resolution

```
# Roll 1 — does encounter happen?
Roll D100
If roll <= (final_encounter_rate * 100) → encounter triggered
Otherwise → no encounter, keep walking

# Roll 2 — which formation? (only if Roll 1 triggered)
Roll D100
Walk encounter_group entries by cumulative weight
→ formation selected
```

| Scenario | Base | Modifier | Final |
|---|---|---|---|
| No Rogue | 0.15 | 0 | 0.15 |
| Rogue + stealth cloak | 0.15 | -0.15 | 0.00 |
| Rogue + lure charm | 0.15 | +0.20 | 0.35 |
| Rogue + both | 0.15 | +0.05 | 0.20 |

> **Design note:** Stacking multiple accessories is naturally limited by the accessory slot count per character — no additional cap needed.

> Boss battles use `encounter_rate: 1.0` + `once: true` — they are **scripted events, not random rolls**. Encounter modifier should be **ignored entirely** for boss encounters.


**Typical encounter**

```yaml
encounter_rate: 0.15             # required — drives the roll
encounter_group: forest_enemies  # required — enemy pool or specific boss
once: false                      # optional, default false
```

**Boss Event Encount**

```yaml
encounter_rate: 1.0             # required — always 100%
encounter_group: boss_001       # required — enemy pool or specific boss
once: true                      # optional, default false
on_complete:                    # optional, omit if no hooks
  set_flag: boss_dragon_defeated
  start_dialogue: elder_aftermath
```

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
PT, items, flags all restored to save state
Nothing is lost beyond progress since last save

## Save State Restored

- character status (hp, mp, status effects)
- party repository (items, pt)
- flags
- map location

