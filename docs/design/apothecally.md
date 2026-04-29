# 7. Apothecary

**Core Model**: An NPC service station — player supplies materials + pays `gp` fee → receives output item. 100% success, no gambling.

## Recipe System

```yaml
id: recipe_hi_potion
scroll_name: "Vital Brew"        # always visible, intentionally vague
output:
  item: hi_potion                # output item id (resolved at craft time)
  qty: 2                         # crafted quantity per craft
inputs:
  mc:                            # magic-core inputs (optional)
    - size: S
      qty: 1
  items:                         # material inputs (optional)
    - id: herb_red
      qty: 2
    - id: rare_herb
      qty: 1
gp_cost: 180                     # GP fee per craft
unlock_flag: story_act2_started  # recipe is locked until this flag is set
unique_output: true              # optional — once player owns the output,
                                 # recipe stays visible but uncraftable.
                                 # Use for key items (e.g. veil_breaker).
```

The output item's display name is read from the item catalog (it is **not**
duplicated on the recipe). Lock-state flavor text is rendered by the UI.

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

## Recipe Unlock Summary

| Scroll Name | Output | Unlock | Key Inputs |
|---|---|---|---|
| Purging Salve | Remedy ×1 | Act 1 | Venom Sac, Red Herb |
| Arcane Tonic | Ether ×2 | Act 1 | MC-S, Mana Droplet |
| Vital Brew | Hi-Potion ×2 | Act 2 | MC-S, Rare Herb |
| Clarity Brew | Hi-Ether ×2 | Act 2 | MC-M, Water Crystal |
| Alchemist's Lens | Veil Breaker ×1 | Act 2 | MC-M, Spirit Orb, Ectoplasm |
| Volatile Concoction | Fire Vial ×3 | Act 2 | Fire Gland, Venom Sac |
| Sacred Mixture | Holy Water ×3 | Act 3 | MC-S, Spirit Orb |
| Searing Mixture | Ice Vial ×3 | Act 3 | Ice Fang, Wind Crystal |
| Forbidden Brew | Life Crystal ×1 | Act 3 | MC-L, Soul Fragment, Phantom Veil |
| Grand Elixir | Elixir ×1 | Act 4 | MC-L, MC-M ×2, Soul Fragment |

## Notes

- `veil_breaker` outputs `qty: 1` and is a key item — duplicate crafting is
  blocked via `unique_output: true` (see schema).
- All current recipe inputs are **consumed** on craft. There is no
  presence-check (uncomsumed) input mode in V1.
- Shock Vial is currently included in Act 3 for wind-element coverage.