# 6. Currency

- Unit: `GP` (Guild Point)
- Source: Monster drops `Magic Core` → exchange at `Magic Core Shop` → `GP`
- `GP` tied to `Party Repository` (story-consistent)
- `Magic Core` dual-use: currency OR crafting material

| Approach | Feel | Risk |
|---|---|---|
| Sell cores for GP, buy materials separately | Clean economy | Feels disconnected |
| Cores are the only crafting input | Tight resource tension | Player may never craft |
| **Cores for crafting, GP earned separately** | Best separation | Needs a second GP source |
| Tiered cores (low → GP, high → craft only) | Elegant | More complex to balance |

**Recommendation: tiered cores** — small/common cores → exchanged for `GP`, large/rare cores → reserved for crafting. Naturally emerges from your "size and color drives value" note.

**Suggested `GP` Income Sources**

| Source | Feel |
|---|---|
| Magic Core exchange | Primary grind loop |
| Selling items (0.5x buyback) | Inventory management |
| Quest rewards | Story progression |
| Apothecary outputs sold | Crafting-to-profit loop |

**Currency UX Recommendations**

- Display `GP` balance always visible in HUD — it's the only currency unit, keep it prominent
- Show core → GP exchange rate before confirming at Magic Core Shop
- In shops, show current `GP` balance inline with item price so player never has to mentally subtract
- No `gold` + `GP` split — your single-currency design is cleaner, stick with it
