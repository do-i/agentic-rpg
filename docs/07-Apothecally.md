# 7. Apothecary

**Core Model**: An NPC service station — player supplies materials + pays `gp` fee → receives output item. 100% success, no gambling.

## Recipe System

```
id: recipe_hi_potion
scroll_name: "Vital Brew"        # always visible, intentionally vague
output_name: "Hi-Potion"         # shown only after unlock
locked_label_flavor: "This recipe has not yet been revealed."
output:
  item: hi_potion
  qty: 1
inputs:
  mc:
    - size: L
      qty: 2
    - size: XL
      qty: 1
  items:
    - id: herb_red
      qty: 2
gp_cost: 180
unlock:
  flag: story_phase_08_dragon_cave

```

## Scroll Naming Convention

Names visible from day one, intentionally vague — imply *category* of effect, not specific item. Player can infer "this is probably a heal item" without knowing exactly what.

**Naming pattern:** `[Vague Adjective] [Effect Category] Draught/Tonic/Brew/Salve/Elixir`

| Output Type | Example Scroll Names |
|---|---|
| Heal (HP restore) | *Mending Draught*, *Vital Brew*, *Restorative* |
| MP restore | *Arcane Tonic*, *Mana Salve*, *Clarity Brew* |
| Status cure | *Purging Salve*, *Cleansing Tonic*, *Bitter Cure* |
| Buff (STR/DEX up) | *Warrior's Brew*, *Swiftness Tonic*, *Iron Draft* |
| Battle throw item | *Volatile Concoction*, *Searing Mixture*, *Shock Vial* |
| Rare / unique | *Alchemist's Secret*, *Grand Elixir*, *Forbidden Brew* |

Rare/late recipes get maximally ambiguous names — player knows something's there, not what.

## UI Layout

```
[Apothecary — Recipes]

  ✅  Mending Draught         ← ready (full color, selectable)
  ✅  Vital Tonic (grayed)    ← unlocked inputs missing
  🔓  Warrior's Brew          ← locked but has all inputs
  🔒  Purging Salve (grayed)  ← locked and inputs missing
```

Selecting a 🔒 row → no action, or a brief flavor message: *"This recipe has not yet been revealed."*

Note: It's rare to have locked but has all inputs. But, possible. Typical flow should be unlock first then see receipe and search for items.

## State → Visibility Matrix

| Field | Locked 🔒 | Unlocked 🔓 |
|---|---|---|
| Scroll name | ✅ Visible | ✅ Visible |
| Lock/unlock icon | ✅ Visible | ✅ Visible |
| Output item | ❌ Hidden | ✅ Visible |
| Input items | ❌ Hidden | ✅ Visible |
| gp cost | ❌ Hidden | ✅ Visible |
| Craft button | ❌ Disabled | ✅ If ready |

Clean separation — unlock is the gate to all mechanical detail.


## UI Flow
```
[Apothecary NPC]
  └── [Recipes List]
        ├── Filter: Show only unlocked and ready (has all input items)
        ├── [Recipe Row] → recipe name, output item icon, gp cost
        └── [Select Recipe] → Detail Panel
              ├── Output: Elixir ×1
              ├── Inputs:
              │     ├── Herb (Red) ×2
              │     └── Magic Core (S) ×1
              ├── Cost: 150 gp  [Balance: 3,200 gp]
              ├── [Craft]
              └── [Cancel]
```

## Crafting Economy

Most recipes produce items unavailable in stores. A few overlap with store items but at power-premium quality.

**Goal**
Crafted Item is too good to sell.

- Crafting isn't about saving gp — it's about access
- Store covers basics (Potion, Antidote); Apothecary covers Hi-Potion, Elixir, battle throws, buff tonics
- Player isn't doing math to decide whether to craft — they craft because they need that item
- Rare/late recipes feel like genuine power unlocks, not just efficiency plays

For the small overlap category (store also sells it), crafted version could yield qty 2 for roughly the cost of 1 — makes crafting feel efficient without breaking the store economy.

Crafted item is unsellable or 0.5× on craft-exclusive items — you don't want players treating Apothecary as a gp printer. The profit loop should come from selling excess raw materials, not finished crafted goods.
