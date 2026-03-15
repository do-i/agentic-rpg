# Map

- bird-eye view world Map
- character can move 8 directions

```yaml
world:
  name: Rusted Kingdoms
  tagline: "Where magic faded, steam rose — and heroes are still needed."
  blend:
    foundation: Medieval Fantasy
    culture: Steampunk
    backstory: Post-Apocalyptic ruins
  tone: Lighthearted & Whimsical
  story_arc: Hero's Journey
```

## World Map

- enemy is invisible
- town, dungeon entrance is visible on Map

## Town

- no enemy encouter
- NPC hint characters: they give you hint what to do next to progress story
- NPC behavior is flag driven


## Building
- flag based access
- Apothecary (every town has one)
- General Store (buy consumable items, armory)

Note: for convenience NPC apothecary and NPC item seller work in the same store.

## Dungeon

- enemy is invisible; encouter by random chance

## NPC on world map

Clean — `present` as a condition-driven visibility flag is simple mechanism. The NPC simply doesn't exist on the map until the condition is false, then appears and can be talked through.
Wait — actually inverted. The gate NPC should be:

- present when flag is NOT set (blocking)
- gone when flag IS set (passage open)

See data/maps/world.yaml

```yaml
# NPC appears AFTER flag is set (reward giver, story character, etc.)
npcs:
  - id: some_npc
    type: gate
    position: [x, y]
    dialogue: some_dialogue
    present:
      requires: [some_flag]
```

### Use cases this covers

| Scenario | `present` condition |
|---|---|
| Gate NPC blocks until zone cleared | `excludes: [boss_zone04_defeated]` |
| Merchant appears after act starts | `requires: [story_act2_started]` |
| Survivor NPC appears after rescue | `requires: [npc_rescued]` |
| Construction NPC gone after build | `excludes: [shop_blacksmith_unlocked]` |

Essentially the full `requires`/`excludes` pattern from dialogue conditions, applied to NPC presence. Consistent with the rest of the flag system.
