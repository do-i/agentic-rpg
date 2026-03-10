# 10. Enemy Design
## High-Level Categories

| # | Category | One-liner |
|---|---|---|
| 1 | **Stat Block** | HP, ATK, DEF, MRES, DEX, EXP yield, gp/core drop |
| 2 | **Elemental Profile** | Weaknesses, resistances, immunities |
| 3 | **Ability & Move Set** | What actions the enemy can take per turn |
| 4 | **Targeting Logic** | How the enemy picks its target |
| 5 | **Loot Table** | Drop items, drop rates, core tier |
| 6 | **Encounter Grouping** | Solo / pack / mixed — how enemies appear together |
| 7 | **Boss Rules** | Phase transitions, special flags (immune to instant-kill, etc.) |
| 8 | **Enemy Taxonomy** | Type tags: beast, undead, demon, construct — drives weakness/ability interactions |
| 9 | **Scaling & Placement** | Where enemies appear, what level range they target |
| 10 | **Behavior Pattern** | Passive AI logic: aggressive, defensive, support-first, random |

## Taxonomy

| Type | Examples | Key Design Hook |
|---|---|---|
| **Beast** | Wolf, Slime, Dragon | Baseline — drops Magic Core |
| **Undead** | Skeleton, Ghost, Zombie | Weak to Holy; Heal spells deal damage; drops Magic Core |
| **Demon** | Imp, Dark Knight | Weak to Holy; immune to instant-kill; drops Magic Core |
| **Construct** | Golem, Armor | Immune to status effects; drops Magic Core |

## Zone Encounter Sets + Boss

| Zone | Set A | Set B | Boss |
|---|---|---|---|
| **1. Starting Forest** | Wild Wolf, Cave Bat, Cave Spider, Treant, Giant Rat | Cave Bat, Venom Bat, Forest Spider, Wild Wolf, Treant | Forest Spider (Giant) |
| **2. Open Plains** | Forest Wolf, Giant Rat, Horned Rabbit, Sand Serpent, Forest Spider | Forest Wolf, Marsh Rat, Horned Rabbit, Treant, Venom Bat | Mountain Bear |
| **3. Marshland** | Marsh Rat, Marsh Serpent, Marsh Frog, Bog Leech, Mandrake | Marsh Frog, Bog Leech, Water Elemental, Mud Crab, Plague Rat | Mud Crab (King) |
| **4. Ancient Ruins** | Skeleton, Stone Gargoyle, Ghost, Mimic, Will-o-Wisp | Skeleton, Bone Archer, Plague Zombie, Ghost, Stone Gargoyle | Plague Zombie (Ancient) |
| **5. Mountain Foothills** | Stone Golem, Rock Crab, Sand Worm, Wind Elemental, Plague Rat | Iron Golem, Rock Crab, Sand Worm, Wind Elemental, Plague Rat | Wyvern |
| **6. Mountain Pass** | Frost Wolf, Iron Golem, Harpy, Cockatrice, Dark Knight | Frost Wolf, Iron Gargoyle, Harpy, Dark Knight, Cockatrice | Frost Dragon |
| **7. Sunken Cave** | Cave Golem, Bone Archer, Blood Bat, Venom Spider, Dark Skeleton | Cave Golem, Iron Gargoyle, Fungus Spore, Blood Bat, Dark Skeleton | Stone Dragon |
| **8. Corrupted Forest** | Shadow Wolf, Blighted Treant, Phantom, Shadow Imp, Wraith | Cursed Gargoyle, Rot Zombie, Banshee, Shadow Imp, Blighted Treant | Succubus |
| **9. Volcanic Region** | Lava Serpent, Magma Golem, Fire Elemental, Lava Lizard, Cerberus | Magma Golem, Vile Imp, Chimera, Lava Lizard, Fire Elemental | Flame Dragon |
| **10. Final Stronghold** | Ancient Golem, Lich, Chaos Elemental, Specter, Death Knight | Dark Elemental, Fallen Angel, Demon Lord's Guard, Specter, Death Knight | Dullahan |

**Notes:**
- Boss names marked with a qualifier (Giant, King, Ancient) to distinguish from any random encounter version
- Zone 5 sets A/B are nearly identical — worth differentiating later if needed

## Weight Distribution

### Zone 1 — Starting Forest
*Staples: Cave Bat, Wild Wolf, Treant*

| Formation | Set A | Set B |
|---|---|---|
| [Cave Spider, Cave Spider] | 30 | — |
| [Giant Rat, Giant Rat] | 25 | — |
| [Wild Wolf, Cave Spider] | 20 | — |
| [Venom Bat, Venom Bat] | — | 30 |
| [Forest Spider] | — | 30 |
| [Venom Bat, Forest Spider] | — | 15 |
| [Wild Wolf] | 10 | 10 |
| [Cave Bat] | 10 | 10 |
| [Treant] | 5 | 5 |

---

### Zone 2 — Open Plains
*Staples: Forest Wolf, Horned Rabbit*

| Formation | Set A | Set B |
|---|---|---|
| [Giant Rat, Giant Rat, Giant Rat] | 30 | — |
| [Sand Serpent] | 25 | — |
| [Forest Spider, Giant Rat] | 20 | — |
| [Marsh Rat, Marsh Rat] | — | 30 |
| [Treant, Venom Bat] | — | 25 |
| [Marsh Rat, Venom Bat] | — | 20 |
| [Forest Wolf] | 10 | 10 |
| [Horned Rabbit] | 10 | 10 |
| [Forest Wolf, Horned Rabbit] | 5 | 5 |

---

### Zone 3 — Marshland
*Staples: Marsh Frog, Bog Leech*

| Formation | Set A | Set B |
|---|---|---|
| [Marsh Rat, Marsh Rat] | 30 | — |
| [Marsh Serpent] | 25 | — |
| [Mandrake] | 20 | — |
| [Water Elemental] | — | 30 |
| [Mud Crab] | — | 25 |
| [Plague Rat, Plague Rat] | — | 20 |
| [Marsh Frog] | 10 | 10 |
| [Bog Leech] | 10 | 10 |
| [Marsh Frog, Bog Leech] | 5 | 5 |

---

### Zone 4 — Ancient Ruins
*Staples: Skeleton, Ghost, Stone Gargoyle*

| Formation | Set A | Set B |
|---|---|---|
| [Mimic] | 30 | — |
| [Will-o-Wisp, Will-o-Wisp] | 25 | — |
| [Skeleton, Will-o-Wisp] | 20 | — |
| [Bone Archer, Bone Archer] | — | 30 |
| [Plague Zombie, Plague Zombie] | — | 25 |
| [Bone Archer, Plague Zombie] | — | 20 |
| [Skeleton] | 10 | 10 |
| [Ghost] | 5 | 5 |
| [Stone Gargoyle] | 10 | 10 |

---

### Zone 5 — Mountain Foothills
*Staples: Rock Crab, Sand Worm, Wind Elemental*

| Formation | Set A | Set B |
|---|---|---|
| [Stone Golem, Stone Golem] | 30 | — |
| [Plague Rat, Plague Rat] | 25 | — |
| [Stone Golem, Plague Rat] | 20 | — |
| [Iron Golem, Iron Golem] | — | 30 |
| [Iron Golem, Rock Crab] | — | 25 |
| [Iron Golem, Sand Worm] | — | 20 |
| [Rock Crab] | 10 | 10 |
| [Sand Worm] | 10 | 10 |
| [Wind Elemental] | 5 | 5 |

---

**Updated Zone 6 — Mountain Pass**
*Staples: Frost Wolf, Harpy, Dark Knight*

| Formation | Set A | Set B |
|---|---|---|
| [Iron Golem, Griffon] | 30 | — |
| [Griffon, Griffon] | 25 | — |
| [Iron Golem, Frost Wolf] | 20 | — |
| [Iron Gargoyle, Iron Gargoyle] | — | 30 |
| [Griffon, Iron Gargoyle] | — | 25 |
| [Iron Gargoyle, Frost Wolf] | — | 20 |
| [Frost Wolf] | 10 | 10 |
| [Harpy] | 10 | 10 |
| [Dark Knight] | 5 | 5 |

---

### Zone 7 — Sunken Cave
*Staples: Cave Golem, Blood Bat*

| Formation | Set A | Set B |
|---|---|---|
| [Venom Spider, Venom Spider] | 30 | — |
| [Bone Archer, Dark Skeleton] | 25 | — |
| [Dark Skeleton, Dark Skeleton] | 20 | — |
| [Iron Gargoyle, Iron Gargoyle] | — | 30 |
| [Fungus Spore, Fungus Spore] | — | 25 |
| [Iron Gargoyle, Fungus Spore] | — | 20 |
| [Cave Golem] | 10 | 10 |
| [Blood Bat, Blood Bat] | 10 | 10 |
| [Cave Golem, Blood Bat] | 5 | 5 |

---

### Zone 8 — Corrupted Forest
*Staples: Shadow Imp, Blighted Treant*

| Formation | Set A | Set B |
|---|---|---|
| [Shadow Wolf, Shadow Wolf] | 30 | — |
| [Phantom, Phantom] | 25 | — |
| [Wraith, Shadow Wolf] | 20 | — |
| [Rot Zombie, Rot Zombie] | — | 30 |
| [Cursed Gargoyle, Rot Zombie] | — | 25 |
| [Banshee] | — | 20 |
| [Shadow Imp] | 10 | 10 |
| [Blighted Treant] | 10 | 10 |
| [Shadow Imp, Blighted Treant] | 5 | 5 |

---

### Zone 9 — Volcanic Region
*Staples: Magma Golem, Lava Lizard*

| Formation | Set A | Set B |
|---|---|---|
| [Lava Serpent, Lava Serpent] | 30 | — |
| [Fire Elemental, Lava Serpent] | 25 | — |
| [Cerberus] | 20 | — |
| [Vile Imp, Vile Imp] | — | 30 |
| [Chimera] | — | 25 |
| [Vile Imp, Chimera] | — | 20 |
| [Magma Golem] | 10 | 10 |
| [Lava Lizard] | 10 | 10 |
| [Magma Golem, Lava Lizard] | 5 | 5 |

---

### Zone 10 — Final Stronghold
*Staples: Specter, Death Knight*

| Formation | Set A | Set B |
|---|---|---|
| [Ancient Golem, Ancient Golem] | 30 | — |
| [Lich, Ancient Golem] | 25 | — |
| [Chaos Elemental, Lich] | 20 | — |
| [Dark Elemental, Dark Elemental] | — | 30 |
| [Fallen Angel] | — | 25 |
| [Demon Lord's Guard, Dark Elemental] | — | 20 |
| [Specter] | 10 | 10 |
| [Death Knight] | 10 | 10 |
| [Specter, Death Knight] | 5 | 5 |

## Enemy Drop Key Points
- MC drop quantity/tier can vary by enemy type, level, or rarity — but floor is always 1
- Item drops are the only variable outcome — keeps reward feel consistent while adding lottery excitement
- Boss encounters would naturally drop more MC + guaranteed rare item on top of this baseline
- Upon enemy flee, always drop at least one item


## Barrier Enemies

| Zone | Enemy | Type | Notes |
|---|---|---|---|
| 4 | Ghost | Undead | Mid-early wall |
| 5 | Wind Elemental | Demon | Mid wall |

**Implications:**

- Player first encounters Ghost in Zone 4 — deals 0 damage, realizes something is wrong
- Veil Breaker becomes a goal to unlock before or during Zone 5
- Wind Elemental reinforces the mechanic in the next zone — confirms it's a system, not a bug
- Both enemies still appear in random encounter sets — they're not rare, so the player hits them often enough to feel the friction

**Open design questions to resolve later:**

| Question | Options |
|---|---|
| Veil Breaker consumed or permanent? | Permanent |
| Unique drop from barrier enemies? | Yes — rare item only they carry |
| UI feedback when hitting barrier enemy | "A mysterious force blocks your attack" |

## Stat Scaling Framework

### Zone → Stat Range

| Zone | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---|---|---|---|
| 1 | 20-40 | 8-12 | 3-6 | 2-4 | 8-12 | 20-40 |
| 2 | 35-55 | 11-15 | 5-8 | 3-6 | 10-14 | 35-60 |
| 3 | 50-75 | 14-18 | 7-11 | 5-8 | 12-16 | 55-85 |
| 4 | 70-100 | 17-22 | 10-14 | 8-12 | 14-18 | 80-120 |
| 5 | 95-130 | 21-26 | 13-17 | 11-15 | 16-20 | 115-160 |
| 6 | 125-165 | 25-31 | 16-21 | 14-18 | 18-23 | 155-210 |
| 7 | 160-205 | 30-37 | 20-26 | 17-22 | 21-26 | 205-265 |
| 8 | 200-250 | 36-44 | 25-32 | 21-27 | 24-30 | 260-330 |
| 9 | 245-300 | 43-52 | 31-39 | 26-33 | 28-35 | 325-405 |
| 10 | 295-380 | 51-63 | 38-48 | 32-41 | 33-42 | 400-510 |

Boss multiplier: `x2.5 HP`, `x1.5 ATK/DEF/MRES`, `x3 EXP`

### Type modifiers

| Type | HP | ATK | DEF | MRES | DEX |
|---|---|---|---|---|---|
| Beast | base | base | base | base | base |
| Undead | +10% | base | base | +15% | -10% |
| Construct | +20% | base | +25% | -20% | -15% |
| Demon | base | +15% | base | +10% | +10% |

### Core Stats (stored on enemy)

| Stat | Key | Role |
|---|---|---|
| Hit Points | `hp` | Combat survival |
| Attack | `atk` | Physical damage output |
| Defense | `def` | Reduces incoming physical damage |
| Magic Resistance | `mres` | Reduces incoming spell damage |
| Dexterity | `dex` | Turn order, hit chance |
| Type | `type` | beast / undead / demon / construct |

---

### Reward Stats (stored on enemy)

| Stat | Key | Notes |
|---|---|---|
| EXP yield | `exp` | Fixed value per enemy |
| Magic Core tier | `mc_tier` | `small` / `large` — drives crafting vs gp economy |
| Magic Core qty | `mc_qty` | Min 1, can be a range e.g. `1-3` |
| Item drops | `loot_table` | Reference to loot table id |

### What's intentionally excluded

| Stat | Reason |
|---|---|
| MP | Enemies don't manage MP — ability use is just pattern/turn-based |
| STR / CON / INT | No level-up system; `atk` and `mres` are direct finals |
| Level | Implicit via stat values and placement — no need to store |

## Magic Core (MC)

Size is the only axis — value emerges from the combination.

| Size | Key | Role |
|---|------|------|
| Tiny | `XS` | Bulk common drop, primary gp source |
| Small | `S` | Standard drop |
| Medium | `M` | Mid crafting material |
| Large | `L` | Rare drop, advanced crafting |
| Huge | `XL` | Boss-only, end-game recipes |


## MC Exchange Rate

| Size | GP value | Ratio |
|---|---|---|
| XS | 1 gp | baseline |
| S | 10 gp | ×10 |
| M | 100 gp | ×10 |
| L | 1,000 gp | ×10 |
| XL | 10,000 gp | ×10 |

**Example Bundle Value**

`1L + 2M + 5XS` = 1,000 + 200 + 5 = **1,205 gp** if fully exchanged


## Key Design Points

- XS is nearly worthless solo — meaningful only in bulk
- XL from boss = 10,000 gp if exchanged — but recipe value should far exceed that to discourage selling
- Easy mental math for player — power of 10 is instantly readable
- Recipe costs in gp now have a clear anchor: a recipe costing 500 gp = 5 S cores worth of exchange value
- Crafting tension is sharp: **1 XL sold = 10,000 gp vs. used in end-game recipe** — that's a real decision


## Example

```yaml
id: forest_wolf
name: Forest Wolf
type: beast
hp: 45
atk: 12
def: 6
mres: 2
dex: 14
exp: 38  # player gets this EXP
drops:
  mc:
    - size: XS
      qty: 3
    - size: S
      qty: 1
  loot:
    - pool:
        - item: wolf_fang
          weight: 80
        - item: wolf_pelt
          weight: 20
    - pool:
        - item: sharp_claw
          weight: 15
        - item: rare_wolf_gem
          weight: 5
        # weights sum to 20 → 80% nothing
```
- Each pool is resolved independently — one roll per pool.
- Value = what the player chooses to do with the bundle — exchange small ones for gp, hoard large ones for crafting.

**One design decision to make:** `mc_tier` fixed per enemy, or weighted random between small/large? Fixed is simpler for V1 — rare enemies and bosses always drop `large`, commons always drop `small`.

**Suggested drill-down order** — each feeds the next:

Move Set → Targeting Logic → Behavior Pattern → Loot Table → Encounter Grouping → Boss Rules → Scaling & Placement