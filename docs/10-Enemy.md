# 10. Enemy Design
## High-Level Categories

| # | Category | One-liner |
|---|---|---|
| 1 | **Stat Block** | HP, ATK, DEF, MRES, DEX, EXP yield, pt/core drop |
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

## Enemy Drop Key Points
- MC drop quantity/tier can vary by enemy type, level, or rarity — but floor is always 1
- Item drops are the only variable outcome — keeps reward feel consistent while adding lottery excitement
- Boss encounters would naturally drop more MC + guaranteed rare item on top of this baseline
- Upon enemy flee, always drop at least one item

## Stat Block Design

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
| Magic Core tier | `mc_tier` | `small` / `large` — drives crafting vs pt economy |
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
| Tiny | `XS` | Bulk common drop, primary pt source |
| Small | `S` | Standard drop |
| Medium | `M` | Mid crafting material |
| Large | `L` | Rare drop, advanced crafting |
| Huge | `XL` | Boss-only, end-game recipes |


## MC Exchange Rate

| Size | PT value | Ratio |
|---|---|---|
| XS | 1 pt | baseline |
| S | 10 pt | ×10 |
| M | 100 pt | ×10 |
| L | 1,000 pt | ×10 |
| XL | 10,000 pt | ×10 |

**Example Bundle Value**

`1L + 2M + 5XS` = 1,000 + 200 + 5 = **1,205 pt** if fully exchanged


## Key Design Points

- XS is nearly worthless solo — meaningful only in bulk
- XL from boss = 10,000 pt if exchanged — but recipe value should far exceed that to discourage selling
- Easy mental math for player — power of 10 is instantly readable
- Recipe costs in pt now have a clear anchor: a recipe costing 500 pt = 5 S cores worth of exchange value
- Crafting tension is sharp: **1 XL sold = 10,000 pt vs. used in end-game recipe** — that's a real decision


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
exp: 38 # player gets this EXP
mc_drop: # drops at least one
  - size: XS
    qty: 5
  - size: M
    qty: 2
  - size: L
    qty: 1
loot_table: loot_forest_wolf
```

Value = what the player chooses to do with the bundle — exchange small ones for pt, hoard large ones for crafting.

**One design decision to make:** `mc_tier` fixed per enemy, or weighted random between small/large? Fixed is simpler for V1 — rare enemies and bosses always drop `large`, commons always drop `small`.

**Suggested drill-down order** — each feeds the next:

Move Set → Targeting Logic → Behavior Pattern → Loot Table → Encounter Grouping → Boss Rules → Scaling & Placement