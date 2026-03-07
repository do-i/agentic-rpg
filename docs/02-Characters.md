# 2. Characters

## Party Member Data Model
```yaml
# party/member.yaml
id: sera
name: Sera
class: sorcerer
level: 5
exp: 1240
hp: 38
hp_max: 38
mp: 52
mp_max: 60
str: 8
dex: 14
con: 9
int: 22
equipped:
  weapon: staff_oak
  armor: robe_silk
  shield: none        # sorcerer can't equip shields
abilities_unlocked: [fireball]
status_effects: []
```

## Status

**Player Stats:**

| Stat | Key | Role |
|------|-----|------|
| Level | `level` | Gates spells and equipment access |
| Experience | `exp` | Accumulates to trigger level-up |
| Gold | `gold` | Currency for shops |
| Hit Points | `hp` / `hp_max` | Combat survival |
| Magic Points | `mp` / `mp_max` | Spell resource |
| Strength | `str` | Physical attack damage |
| Dexterity | `dex` | Hit rate, crit chance, turn order |
| Constitution | `con` | HP growth per level, poison resistance |
| Intelligence | `int` | Spell damage, MP growth per level |

## Level

**Threshold Formula**
```
exp_required(level) = exp_base * (level ^ 2.0)

exp_required(level) = exp_base * (level ^ exp_factor)
```

Example

| Level | Hero (base 100) | Mage (base 95) | Rogue (base 90) |
|---|---|---|---|
| 2 | 200 | 190 | 180 |
| 5 | 1,118 | 1,062 | 1,006 |
| 10 | 3,162 | 3,004 | 2,846 |
| 20 | 8,944 | 8,497 | 8,050 |
| 50 | 35,355 | 33,587 | 31,820 |
| 100 | 100,000 | 95,000 | 90,000 |

### Exp Rules
- Cumulative — total EXP ever earned, never resets
- Level-up triggers when total_exp >= exp_required- (next_level)
- EXP cap: 1,000,000 (from doc 01)
- Level cap: 100
- KO'd members get 0 EXP

### Level-up table format
```yaml
# classes/hero.yaml
class: hero
base_hp: 20
base_mp: 8
stat_growth:
# index = level-1, cycles if level > array length
  str:  [2, 2, 3, 2, 3, 2, 3, 3, 2, 3]   # per level 1..N
  dex:  [1, 2, 1, 2, 2, 1, 2, 2, 2, 2]
  con:  [2, 2, 2, 3, 2, 2, 3, 2, 2, 3]
  int:  [1, 1, 1, 1, 2, 1, 1, 2, 1, 2]
exp_curve: quadratic     # linear | quadratic | custom
exp_base: 100
exp_factor: 2.0
```

### HP/MP Growth

```
hp_gain per level = con + 6
mp_gain per level = int + 6

```
- Full HP/MP restore on level-up ✅
- Current HP/MP set to new `hp_max` / `mp_max`

### Mix/Max HP/MP at Level 1 and 100

| Class | HP@1 | HP@100 | MP@1 | MP@100 |
|---|---|---|---|---|
| Warrior | 28 | **928** | 0 | **700** |
| Hero | 22 | **872** | 10 | **740** |
| Cleric | 18 | **868** | 18 | **918** |
| Mage | 14 | **764** | 20 | **970** |
| Rogue | 16 | **766** | 6 | **706** |


### Level-up Event Flow
1. EXP added post-battle
2. Check total_exp >= exp_required(next_level)
3. Increment level
4. Apply stat_growth for new level
5. Recalculate hp_max, mp_max
6. Full restore HP/MP
7. Check ability unlock (level-gated)
8. Show level-up screen
9. Repeat from 2 (multi-level possible in one battle)

## Class

| # | Class | Role | Primary Stats | Element |
|---|-------|------|---------------|---------|
| 1 | **Hero** | Balanced fighter / party leader | STR, CON | — |
| 2 | **Warrior** | Tank, high DEF, physical damage | STR, CON | — |
| 3 | **Mage** | Offensive spells, fragile | INT, DEX | Fire / Ice / Wind |
| 4 | **Cleric** | Heals, buffs, light offense | INT, CON | Earth / Holy |
| 5 | **Rogue** | High speed, crit, utility | DEX, STR | — |

**Design notes:**
- Hero is intentionally generic — good for the scenario-defined protagonist
- Warrior + Hero covers physical front line; Rogue acts first due to high DEX
- Mage vs. Cleric splits INT usage cleanly: damage vs. support
- Elemental coverage: Mage handles offensive elements, Cleric handles earth/healing magic
- Rogue's utility (e.g., flee success rate, chest traps, encounter rate reduction) fits naturally with your encounter system

## Ability

Each class has set of abilities. When EXP reachs certain point, new ability is realized.

**Ability unlock ideas per class:**

| Class | Early | Mid | Late |
|-------|-------|-----|------|
| Hero | Power Strike | Rally (party DEF up) | Limit Slash |
| Warrior | Shield Bash | Taunt | Fortress Stance |
| Mage | Fireball | Chain Lightning | Meteor |
| Cleric | Heal | Cure Status | Revive |
| Rogue | Steal | Shadow Step | Assassinate |

**Elemental affinities:**
* fire, water, wind, earth


| type | Used by | Formula |
|------|---------|---------|
| `physical` | Hero, Warrior, Rogue | `(str + weapon_atk - enemy_def) * damage_coeff` |
| `spell` | Mage, Cleric | `int * spell_coeff - enemy_mres` |
| `heal` | Cleric, Hero | `int * heal_coeff` or `hp_max * heal_pct` |
| `buff` | All | No damage — applies `effect` block |
| `debuff` | Hero, Rogue | No damage — applies `effect` block |
| `utility` | Rogue, Cleric | Custom logic (steal, cure status) |

One thing worth noting: Warrior has `base_mp: 0` and all his abilities have `mp_cost: 0` — he's entirely resource-free, which is a clean differentiator from the other classes.
