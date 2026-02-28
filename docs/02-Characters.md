# 2. Characters

## Party Member Data Model
```yaml
# party/member.yaml
id: sera
name: Sera
class: mage
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
  shield: null        # mage can't equip shields
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

### Level

**Level-up table format** (per class, defined in plugin):
```yaml
# classes/hero.yaml
class: hero
base_hp: 20
base_mp: 8
stat_growth:
  str:  [2, 2, 3, 2, 3, 2, 3, 3, 2, 3]   # per level 1..N
  dex:  [1, 2, 1, 2, 2, 1, 2, 2, 2, 2]
  con:  [2, 2, 2, 3, 2, 2, 3, 2, 2, 3]
  int:  [1, 1, 1, 1, 2, 1, 1, 2, 1, 2]
exp_curve: quadratic     # linear | quadratic | custom
exp_base: 100
exp_factor: 1.5
```

## Class


| # | Class | Role | Primary Stats | Element |
|---|-------|------|---------------|---------|
| 1 | **Hero** | Balanced fighter / party leader | STR, CON | — |
| 2 | **Warrior** | Tank, high DEF, physical damage | STR, CON | — |
| 3 | **Mage** | Offensive spells, fragile | INT, DEX | Fire / Ice / Wind |
| 4 | **Cleric** | Heals, buffs, light offense | INT, CON | Earth / Holy |
| 5 | **Rogue** | High speed, crit, utility | DEX, STR | — |

**Design notes:**
- Hero is intentionally generic — good for the plugin-defined protagonist
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
