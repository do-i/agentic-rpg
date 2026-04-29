# 4. Infinity Bag System

Each party member carries a personal Infinity Bag — a magical conduit to a single shared `Party Repository`. Any member can deposit or withdraw at any time, from anywhere. The bag itself is weightless and pocketless — it's just a portal.
```
[Aric's Bag] ──┐
[Jep's Bag ] ──┼──▶  Party Repository  (one shared pool)
[Kael's Bag] ──┘
```

- Key item (cannot buy or sell or discard)
- Consumable item (loose when used)
- Non-consumable item (never lose upon usage)
- UI: name, value
- Tags: Every item can have `Tags`: `all`, `battle`, `consumable`, `rare`, `material`, `key`, `sell_soon`
- User may create custom tag with guardrails: name length
- Limit each item to have 5 tags.

**UI FLow**
```
[Item Detail] → [Edit Tags]
  ├── System Tags: [battle ✓] [consumable ✓] [rare]   ← toggle only
  └── Custom Tags: [sell soon ✓] [+New Tag...]         ← toggle + create
```
Note: Optionally add custom tag.


```
# item in Party Repository
id: elixir
tags: [consumable, battle, rare]
locked: true   # prevents sell/discard regardless of tag
```
Sell UI: filter by tag, show only non-locked items → "Sell all [consumable]"
