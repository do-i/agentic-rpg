## Design Gap Audit

Based on all docs reviewed, here are the open areas:

### 🟡 Medium (needed before content complete)

| Area | Gap |
|---|---|
| **Barrier enemy — Veil Breaker** | Referenced but no item definition, no acquisition path |
| **Map/town configs** | Only `town_01` partially defined; zones 2–10 missing |
| **Non-English protagonist name** | `18-NewGame.md` explicitly flags this as open |

### 🟢 Minor / Polish

| Area | Gap |
|---|---|
| **Settings screen** | Flagged in `TODO.md` |
| **Inn cost table** | "TBD" in `06-Map.md` |
| **Sorcerer zone 7 encounter** | Zone 7 uses `iron_gargoyle` (zone 6 enemy) in set_b — possibly intentional, worth confirming |

---

**Suggested priority order:** Save schema → Enemy AI → Item master → Row damage → Veil Breaker