# 5. Equipment System Design

```
General Store
├── Buy Tab
│   ├── [Item List] — shows name, price, stock
│   └── [Select Item] → Detail Panel
│       ├── Description
│       ├── Price
│       ├── Status preview per character
│       │     ├── Aric:  STR 8 → 10▲, DEF 5 → 5
│       │     ├── Elise: [grayed — cannot equip]
│       │     └── Kael:  STR 7 → 8▲
│       └── [Buy] / [Cancel]
│
└── Sell Tab
    ├── Source: Party Repository
    ├── Sell price = buy_price * 0.5
    └── [Select Item] → Detail Panel
        ├── Description
        ├── Sell value
        └── [Sell] / [Cancel]
```

**Key Design Decisions**

- Sell price = 0.5 buy — simple, consistent, no per-item override needed unless you want variance later
- Party Repository as sell source — no per-character inventory to manage; clean
- Gray-out for class restriction vs. net-negative — two distinct states worth distinguishing visually (locked vs. just bad)
- Preview is per-character — shows real equipped-item diff, so the player always sees marginal gain, not absolute stats
- buy/sell equipment only via `Party Repository`


```yaml
# items/chainmail.yaml
id: chainmail
type: armor
buy_price: 800
sell_price: 400        # derived: buy * 0.5, or explicitly set
class_restriction: [hero, warrior]  # omit = all classes
stats:
  def: +15
  dex: -2
description: "Heavy linked armor. Slows movement but shrugs off blows."
```

Quality and Cost are determined by base material and design

- Weapon: sword,
- Armer: lether vest, chainmail, adamantite, hiiroikane etc
- Sheild: wood, steal, mythril, dragon scale, etc
- System: at store display price along with status shift up or down

