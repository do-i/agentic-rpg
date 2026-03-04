# Map

- bird-eye view world Map
- character can move 8 directions

## World Map

- enemy is invisible
- town, dungeon entrance is visible on Map

## Bed / Rest Capsule Rest

```yaml
# Inn (town)
type: bed
cost_pt: TBD        # set per town in map config
effect:
  restore: [hp, mp]
  cure: [poison, silence]

# Rest Capsule (field)
type: Rest Capsule
cost: consumable_item
usable: world_map_only   # not inside dungeon
effect:
  restore: [hp, mp]
  cure: [poison, silence]
```

### Rest Capsule as Item

```yaml
# items/rest_capsule.yaml
id: rest_capsule
type: consumable
use_context: [world_map, dungeon, town]    # anywhere except battle
effect:
  restore: [hp, mp]
  cure: [poison, silence]
buy_price: 500
sell_price: 250
```

### Inn Cost

Defined per town in map config — cheaper in early towns, pricier later

```yaml

# map/town_01.yaml
inn:
  cost_pt: 50
```

## Transportation

- walk
- fly
- sail
- warp

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