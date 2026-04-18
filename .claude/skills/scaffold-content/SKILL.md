---
name: scaffold-content
description: This skill should be used when the user wants to "add an enemy", "create an item", "add an NPC", "write dialogue", "create an encounter zone", "add a consumable", "add a key item", "add a material", "add an accessory", "scaffold game content", or needs to add any new content to the rusted_kingdoms scenario. Generates correct YAML with required fields filled in and tells the user exactly where to place the file.
version: 0.1.0
---

# Scaffold Content — Rusted Kingdoms JRPG

Generate correct YAML stubs for new scenario content and tell the user where to place them.

## Content Types and File Locations

| Type | File location | Registration |
|---|---|---|
| Enemy | `rusted_kingdoms/data/enemies/enemies_rank_<RANK>_<TIER>.yaml` | Auto-loaded by ID — no manifest change needed |
| Consumable | `rusted_kingdoms/data/items/consumables_<tier>.yaml` | Auto-loaded by ID — no manifest change needed |
| Key item | `rusted_kingdoms/data/items/key_items.yaml` | Auto-loaded by ID — no manifest change needed |
| Material | `rusted_kingdoms/data/items/materials.yaml` | Auto-loaded by ID — no manifest change needed |
| Accessory | `rusted_kingdoms/data/items/accessories.yaml` | Auto-loaded by ID — no manifest change needed |
| Dialogue | `rusted_kingdoms/data/dialogue/<id>.yaml` | Referenced by NPCs in map YAML via `dialogue:` field |
| NPC | Edit map YAML `rusted_kingdoms/data/maps/<map_id>.yaml` | Inline in map file — no separate file |
| Encounter zone | `rusted_kingdoms/data/encount/<zone_id>.yaml` | Auto-loaded — referenced by map TMX layer name |

Existing rank files: `enemies_rank_1_SS.yaml` through `enemies_rank_8_F.yaml`. Ranks SS→F map to tiers 1→8. Multiple enemies share one file (separated by `---`).

## ID Naming Convention

IDs must be `lowercase_with_underscores`. Examples: `forest_spider_giant`, `potion_small`, `key_rusty_cell`. IDs must be globally unique within their content category.

## Workflow

1. Ask which content type to create (if not stated).
2. Ask for the key details listed in the "Minimum required fields" section below.
3. Generate the YAML stub (required fields filled in, commonly-used optional fields included with sensible defaults or as comments).
4. Tell the user exactly which file to append it to (or create if it doesn't exist).
5. If the content needs to be wired to something else (e.g., dialogue needs an NPC reference, an NPC needs a map entry), provide that snippet too.

## Minimum Required Fields Per Type

### Enemy
- `id`, `name`, `type` (beast/demon/undead/construct/etc.), `rank` (SS/S/A/B/C/D/E/F)
- `hp`, `atk`, `def`, `mres`, `dex`, `exp`

### Consumable
- `id`, `name`, `use_context` (list of: `battle`, `world_map`, `town`, `dungeon`)
- At least one `effect` key: `restore_hp`, `restore_mp`, or `revive_hp_pct`
- `sell_price`

### Key Item
- `id`, `name`
- `usable` (bool)

### Material
- `id`, `name`, `sell_price`

### Accessory
- `id`, `name`
- `equippable` (list of class IDs, or `["all"]`)
- `sell_price`

### Dialogue (NPC)
- `id`, `type` (usually `npc`)
- At least one entry with `lines`

### NPC (added to a map YAML)
- `id`, `position` ([x, y] tile coords), `dialogue` (dialogue file ID)

### Encounter Zone
- `id`, `name`, `density` (0.0–1.0)
- At least one `entries` formation with `formation` (list of enemy IDs) and `weight`

## YAML Stubs

Generate these stubs, filling in the user's values. Add `---` separator before enemy stubs (they go into multi-document files).

### Enemy stub

```yaml
---
id: <id>
name: <Name>
type: <beast|demon|undead|construct|...>
rank: <SS|S|A|B|C|D|E|F>
hp: <int>
atk: <int>
def: <int>
mres: <int>
dex: <int>
exp: <int>
# boss: false
drops:
  mc: []
  loot: []
ai:
  pattern: random
  moves:
    - action: attack
      weight: 10
targeting:
  default: random_alive
```

### Consumable stub

```yaml
- id: <id>
  name: <Name>
  type: consumable
  use_context: [battle, world_map]
  effect:
    restore_hp: <int>
  buy_price: null
  sell_price: <int>
  description: ""
```

### Key item stub

```yaml
- id: <id>
  name: <Name>
  type: key
  usable: false
  use_context: null
  effect:
    unlock_flag: ""
  sellable: false
  droppable: false
  description: ""
```

### Material stub

```yaml
- id: <id>
  name: <Name>
  type: material
  sell_price: <int>
```

### Accessory stub

```yaml
- id: <id>
  name: <Name>
  type: accessory
  equippable: [all]
  stats: {}
  buy_price: null
  sell_price: <int>
  description: ""
```

### Dialogue stub (NPC)

```yaml
id: <id>
type: npc
entries:
  - lines:
      - "<Dialogue line 1>"
      - "<Dialogue line 2>"
    # condition:
    #   requires: []
    #   excludes: []
    # on_complete:
    #   set_flag: <flag_id>
```

### NPC snippet (goes inside a map YAML under `npcs:`)

```yaml
  - id: <npc_id>
    name: <Name>
    position: [<x>, <y>]
    dialogue: <dialogue_file_id>
    sprite: ""
    default_facing: down
    animation:
      mode: still
```

### Encounter zone stub

```yaml
id: <zone_id>
name: <Zone Name>
density: 0.15
entries:
  - formation: [<enemy_id>]
    weight: 10
    chase_range: 0
```

## Additional Resources

- **`references/enemy-schema.md`** — Full enemy schema with all optional fields (drops, AI patterns, boss config, barriers, immunities)
- **`references/item-schema.md`** — Full item schemas (consumable, key, material, accessory, field_use)
- **`references/dialogue-schema.md`** — Full dialogue schema with all `on_complete` actions (give_items, join_party, transition, start_battle, shops)
- **`references/encounter-schema.md`** — Full encounter schema with boss config, barrier enemies, backgrounds
