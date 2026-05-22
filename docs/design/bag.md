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

**Item screen layout** (`engine/item/`)
```
[ Filter column ] [ Item list ] [ Detail ]
```
- Tabs span the header at equal width: `All · New · Recovery · Status · Battle · Material · Magic Core · Key`.
- **New** shows only the most recent loot batch. Every loot event (a combat
  victory, a chest) calls `RepositoryState.start_loot_batch()` once and stamps
  its items with that batch; New lists items whose `loot_batch` equals the
  latest issued. The batch sequence is persisted and restored on load.
- The **detail** panel is shown only while the cursor is on a list item — not
  when focus is on the tabs or the filter column.
- The **filter column** (left) lists every owned item with an on/off toggle.
  Hiding an item removes it from the list under all tabs. This visibility state
  is session-only (not saved). Enter it with ← from the list (or ↓ from the
  tabs when the list is empty); ENTER/SPACE toggles.
- The list shows 15 full rows and a half-row peek of the 16th.
