# Shop

Shops are stateless. Every visit shows all items whose `unlock_flag` is
satisfied by current story flags; nothing is depleted, so there is no
restock step. New items are introduced via `unlock_flag`; existing items
are never removed.

## Shop Config Schema

```
# map/town_01.yaml
shop:
  items:
    - id: potion
      buy_price: 100
      unlock_flag: story_quest_started
    - id: hi_potion
      buy_price: 500
      unlock_flag: story_act2_started
    - id: tent
      buy_price: 500
      unlock_flag: story_quest_started
    - id: antidote
      buy_price: 80
      unlock_flag: story_quest_started
```

> Existing scenario YAMLs may carry a `qty` key on shop entries. It is
> currently inert — the engine does not read it — and should be omitted
> from new content.

## Shop Types

A map can host up to three flag-gated shops, each its own top-level YAML
section. A dialogue opens one via `on_complete.open_shop`:

| `open_shop` value | Map YAML section | Manifest sprite section | Typical stock |
|---|---|---|---|
| `item`   | `shop`        | `item_shop`   | consumables |
| `weapon` | `weapon_shop` | `weapon_shop` | weapons |
| `armor`  | `armor_shop`  | `armor_shop`  | body / helmets / shields / accessories |
| `magic_core` | — (catalog-driven) | — | magic cores |

All three item-style shops share the same scene and schema; only the
section they load differs (`SHOP_SECTIONS` in `engine/world/world_map_logic.py`).
If a dialogue on a map opens a shop, that map **must** define the matching
section — the loader raises `ValueError` otherwise. Equipment entries need
no extra fields; `buy_price` here overrides the catalog price shown in
`data/items/*.yaml`.

