## Design Gap Audit

Based on all docs reviewed, here are the open areas:

### 🔴 Critical (blocks implementation)

| Area | Gap |
|---|---|
| **Enemy AI / Move Set** | `10-Enemy.md` lists it as a design category but no actual behavior defined (which ability, when, targeting logic) |
| **Item master list** | Items referenced everywhere (`wolf_fang`, `herb_red`, `elixir`, etc.) but no `items/` schema file exists |
| **Battle resolution — row system** | Front/back row defined in `01-Party.md` but never wired into damage formula in `03-Battle.md` |

### 🟡 Medium (needed before content complete)

| Area | Gap |
|---|---|
| **Apothecary recipes** | Schema defined, zero actual recipes authored |
| **Barrier enemy — Veil Breaker** | Referenced but no item definition, no acquisition path |
| **Map/town configs** | Only `town_01` partially defined; zones 2–10 missing |
| **Non-English protagonist name** | `18-NewGame.md` explicitly flags this as open |
| **Playtime tracking** | Listed in save state fields, no spec |

### 🟢 Minor / Polish

| Area | Gap |
|---|---|
| **Settings screen** | Flagged in `TODO.md` |
| **Inn cost table** | "TBD" in `06-Map.md` |
| **Sorcerer zone 7 encounter** | Zone 7 uses `iron_gargoyle` (zone 6 enemy) in set_b — possibly intentional, worth confirming |

---

**Suggested priority order:** Save schema → Enemy AI → Item master → Row damage → Veil Breaker