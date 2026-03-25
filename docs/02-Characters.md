# 2. Characters

## 🗡️ Aric — Hero | Male | 17

[Portrait](https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=male&body=Body_Color_light&head=Human_Male_light&expression=Neutral_light&armour=Leather_teal&legs=Long_Pants_forest&shoes=Basic_Boots_bluegray&hair=Spiked_ash&shoulders=Epaulets_teal)

**Backstory:** A blacksmith's son from Ardel Village. After his father died in a mysterious fire that consumed their forge, Aric took over running the household for his younger siblings. Quiet and reliable beyond his years. The quest begins when the same flame reappears near Ardel — and only he can see it.

## ✨ Elise — Cleric | Female | 16

[Portrait](https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=female&body=Body_Color_light&head=Human_Male_light&eye_color=Eye_Color_green&eyebrows=Thin_Eyebrows_strawberry&hair=Long_center_part_sandy&clothes=Longsleeve_white&belt=Robe_Belt_white&cape_trim=Cape_Trim_white&cape=Solid_sky&armour=Leather_sky&legs=Straight_skirt_sky&hat=Christmas_Hat_sky&hat_trim=Santa_Trim_yellow&weapon=Simple_staff_simple)

**Backstory:** An orphan raised by the Earth Order temple in Ardel. The sisters who raised her say she was found during a flood — the only survivor. She's never left the village, but has been secretly praying for a reason to help the wider world. Aric's arrival feels like an answered prayer.

## 🔥 Reiya — Sorcerer | Female | 18

[Portrait](https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=female&body=Body_Color_light&head=Human_Male_light&expression=Neutral_light&hair=Bob_side_part_rose&legs=Plain_skirt_pink&dress=Kimono_pink&weapon=Gnarled_staff_brass&clothes=Robe_red)

**Backstory:** Daughter of a disgraced court mage, she taught herself advanced elemental magic using her father's confiscated notes. Sharp and self-sufficient, she ended up in Millhaven running a small "consultation" business — reading ley lines, identifying cursed objects. Joins when she recognizes the Lost Flame signature in Aric's description.

## 🗝️ Jep — Rogue | Male | 15

[Portrait](https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=male&body=Body_Color_light&head=Human_Male_light&expression=Neutral_light&jacket=Tabard_gray&legs=Fur_Pants_fur_tan&socks=Ankle_Socks_walnut&hair=High_and_tight_light%20brown&shoes=Sandals_gray)

**Backstory:** A street kid from a port city who got swept into Ruinwatch chasing rumors of hidden treasure. Surprisingly skilled — picked up lockpicking, scouting, and sleight of hand surviving on his own since age 11. Gets caught snooping around the same ruins the party is exploring. Talks his way out of it. Ends up tagging along because he has nowhere else to go.

## ⚔️ Kael — Warrior | Male | 20

[Portrait](http://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=male&body=Body_Color_light&head=Human_Male_light&eyebrows=Thick_Eyebrows_light%20brown&beard=Basic_Beard_light%20brown&hair=Messy1_light%20brown&armour=Plate_silver&legs=Armour_iron&shoes=Armour_bronze&weapon=Waraxe_waraxe&shoulders=Leather_leather&wrists=Cuffs_leather)

**Backstory:** Enlisted in the royal army at 16, became a guard captain's protégé. Discharged at 19 after refusing to burn a village under orders. Ended up in Frostholm doing odd jobs — chopping wood, escorting merchants through mountain passes. Gruff and tired of people, but the moment the party arrives he recognizes the Lost Flame emblem on Aric's gear. He's seen it before — on the order that got him discharged.

## Party Dynamic at a Glance

| | Aric | Elise | Reiya | Jep | Kael |
|---|---|---|---|---|---|
| Age | 17 | 16 | 18 | 15 | 20 |
| Tone | Steady | Warm | Sharp | Chaotic | Weathered |
| Relationship | Center | Trusts everyone | Trusts data | Trusts nobody yet | Trusts Aric instinctively |

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

| Level | Hero (base 100) | Sorcerer (base 95) | Rogue (base 90) |
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
See story_content/classes

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
| Sorcerer | 14 | **764** | 20 | **970** |
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
| 3 | **Sorcerer** | Offensive spells, fragile | INT, DEX | Fire / Water / Wind |
| 4 | **Cleric** | Heals, buffs, light offense | INT, CON | Earth / Holy |
| 5 | **Rogue** | High speed, crit, utility | DEX, STR | — |

**Design notes:**
- Hero is intentionally generic — good for the scenario-defined protagonist
- Warrior + Hero covers physical front line; Rogue acts first due to high DEX
- Sorcerer vs. Cleric splits INT usage cleanly: damage vs. support
- Elemental coverage: Sorcerer handles offensive elements, Cleric handles earth/healing magic
- Rogue's utility (e.g., flee success rate, chest traps, encounter rate reduction) fits naturally with your encounter system

## Ability

Each class has set of abilities. When EXP reachs certain point, new ability is realized.

**Ability unlock ideas per class:**

| Class | Early | Mid | Late |
|-------|-------|-----|------|
| Hero | Power Strike | Rally (party DEF up) | Limit Slash |
| Warrior | Shield Bash | Taunt | Fortress Stance |
| Sorcerer | Fireball | Chain Lightning | Meteor |
| Cleric | Heal | Cure Status | Revive |
| Rogue | Steal | Shadow Step | Assassinate |

**Elemental affinities:**
* fire, water, wind, earth


| type | Used by | Formula |
|------|---------|---------|
| `physical` | Hero, Warrior, Rogue | `(str + weapon_atk - enemy_def) * damage_coeff` |
| `spell` | Sorcerer, Cleric | `int * spell_coeff - enemy_mres` |
| `heal` | Cleric, Hero | `int * heal_coeff` or `hp_max * heal_pct` |
| `buff` | All | No damage — applies `effect` block |
| `debuff` | Hero, Rogue | No damage — applies `effect` block |
| `utility` | Rogue, Cleric | Custom logic (steal, cure status) |

One thing worth noting: Warrior has `base_mp: 0` and all his abilities have `mp_cost: 0` — he's entirely resource-free, which is a clean differentiator from the other classes.
