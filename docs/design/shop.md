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

