# Item Schema — Full Reference

## File Locations

| Type | File |
|---|---|
| Consumables | `rusted_kingdoms/data/items/consumables_<tier>.yaml` |
| Key Items | `rusted_kingdoms/data/items/key_items.yaml` |
| Materials | `rusted_kingdoms/data/items/materials.yaml` |
| Accessories | `rusted_kingdoms/data/items/accessories.yaml` |
| Field use effects | `rusted_kingdoms/data/items/field_use.yaml` |

All files are YAML sequences (`- id: ...`). Append new entries to the appropriate file.

---

## Consumable — Full Schema

```yaml
- id: potion_small
  name: Small Potion
  type: consumable
  use_context: [battle, world_map, town, dungeon]
  effect:
    restore_hp: 80          # integer, or "full"
    restore_mp: 0
    revive_hp_pct: 0.0      # 0.0–1.0; used for revival items
  buy_price: 50             # null = not sold in shops
  sell_price: 25
  description: "Restores 80 HP."
```

Only one `effect` key is needed. Mix-and-match as appropriate.

---

## Key Item — Full Schema

```yaml
- id: key_rusty_cell
  name: Rusty Cell Key
  type: key
  usable: true              # can be used from inventory
  use_context: [dungeon]    # null if only story-triggered
  effect:
    revive_hp_pct: 0.0
    unlock_flag: "cell_unlocked"
  sellable: false
  droppable: false
  description: "A key to the prison cell."
```

---

## Material — Full Schema

Materials are not buyable. Only sell price is tracked.

```yaml
- id: fang_wolf
  name: Wolf Fang
  type: material
  sell_price: 30
```

---

## Accessory — Full Schema

```yaml
- id: ring_ward
  name: Ward Ring
  type: accessory
  equippable: [all]         # ["all"] or list of class IDs like ["warrior", "mage"]
  stats:
    encounter_modifier: 0.5   # 0.5 = 50% spawn rate; 1.0 = normal; 0.0 = no encounters
    blocks_ability: ""        # ability ID this accessory prevents being used on wearer
  buy_price: 800
  sell_price: 400
  description: "Reduces enemy encounters."
```

---

## Field Use Effects

When a consumable or key item is used outside battle, its field behavior is defined in `field_use.yaml`. Add an entry here if the item should do something when used from the field menu.

```yaml
- id: potion_small          # must match item id
  effect: restore_hp        # restore_hp | restore_mp | restore_full | cure | revive
  target: single_alive      # single_alive | single_ko | all_alive
  amount: 80                # for restore_hp/restore_mp
  cures: []                 # status effects cured: [poison, silence, sleep, ...]
  revive_hp_pct: 0.0        # for revive effect
  consumable: true          # false for key items that aren't consumed on use
```

Items without a `field_use.yaml` entry cannot be used from the field menu (they'll be greyed out or hidden depending on `usable: true/false` in the item definition).
