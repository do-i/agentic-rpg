# 10. Enemy Design

## AI complexity level
Random for regulars, conditional (moves triggered by HP threshold, turn count, party state) for bosses

## Targeting Logic

```yaml
targeting:
  default: random_alive         # random living party member
  overrides:
    - ability: frost_breath
      target: all_party
    - ability: ice_shield
      target: self
    - when: party_hp_lowest     # focus wounded — optional aggression
      target: lowest_hp

```

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

The authoritative roster lives in `rusted_kingdoms/data/encount/zone_*.yaml`
(formations + weights) and `rusted_kingdoms/data/enemies/enemies_rank_*.yaml`
(stat blocks). Read those for the current data — the early-design tables that
used to live here drifted out of date and were removed.

Each zone YAML has the shape shown in `battle.md` (Encounter System):
`entries[]` for random formations and `boss` for the scripted fight.

## Weight Distribution

Per-zone formation weights live in `data/encount/zone_*.yaml`. The previous
hand-authored draft tables drifted from the YAML; refer to the YAML directly.

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
| Magic Core drops | `drops.mc[].size` / `qty` | List of `{size: XS\|S\|M\|L\|XL, qty: int}` |
| Item drops | `drops.loot[].pool[]` | Inline weighted pool — see `loot.md` |

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

## Move Set File Convention

| Enemy type | AI location | Field |
|---|---|---|
| Regular | Inline in `enemies_rank_*.yaml` | `ai:` |
| Boss | Separate file | `ai_ref: boss_move_sets/<id>.yaml` |

Rule: if `boss: true` → use `ai_ref`. Otherwise → inline `ai`.

## Example

```yaml
id: fire_elemental
name: Fire Elemental
type: demon
rank: S
hp: 258
atk: 62  # base +15%
def: 31
mres: 40  # base +10%
dex: 38   # base +10%
exp: 375
drops:
  mc:
    - size: M
      qty: 2
  loot:
    - pool:
        - item: fire_crystal
          weight: 55
        - item: ember_core
          weight: 45
ai:
  pattern: random
  moves:
    - action: attack
      weight: 60
    - action: ability
      id: fire_bolt
      weight: 40

```
- Each pool is resolved independently — one roll per pool.
- Value = what the player chooses to do with the bundle — exchange small ones for gp, hoard large ones for crafting.

MC drop sizes are fixed per enemy (rare enemies / bosses drop larger sizes,
commons drop smaller).

**Suggested drill-down order** — each feeds the next:

Move Set → Targeting Logic → Behavior Pattern → Loot Table → Encounter Grouping → Boss Rules → Scaling & Placement

## Ability Types Needed (boss examples)

| Boss | Abilities needed |
|---|---|
| Forest Spider Giant | Web Shot (slow), Poison Bite |
| Mountain Bear | Maul (high dmg), Roar (ATK down party) |
| Wyvern | Wing Slash (all), Poison Tail |
| Frost Dragon | Frost Breath (all), Ice Shield (DEF up) |
| Dullahan | Death Gaze (instant KO attempt), Shadow Slash |

### Rule of Death Gaze - Instant Death Attack
- Blocked by accessory holy_talisman (to be defined in item master)
- If not blocked → reduces HP to 1 instead of KO
- Keeps threat without frustration