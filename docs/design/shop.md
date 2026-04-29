# Shop

## Restock Rules

- Every rest (inn or Rest Capsule) triggers full restock across all shops
- Stock resets to original qty defined in shop config
- New items added via story flag — existing items never removed

## Shop Config Schema

```
# map/town_01.yaml
shop:
  items:
    - id: potion
      qty: 5
      buy_price: 100
      unlock_flag: story_quest_started
    - id: hi_potion
      qty: 3
      buy_price: 500
      unlock_flag: story_act2_started
    - id: tent
      qty: 3
      buy_price: 500
      unlock_flag: story_quest_started
    - id: antidote
      qty: 5
      buy_price: 80
      unlock_flag: story_quest_started
      
```

