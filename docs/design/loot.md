# 11. Loot

Simple weighted random pick — one roll, one outcome.

## Resolution Algorithm

```
1. Sum all weights         → total = 100
2. Roll random(1, 100) (D100)  → e.g. 73
3. Walk entries top to bottom, accumulate weight
4. First entry where cumulative weight >= roll → that item drops
```

### Example — roll = 73

| Item | Weight | Cumulative | Result |
|---|---|---|---|
| Wolf Fang | 60 | 60 | 73 > 60, skip |
| Wolf Pelt | 30 | 90 | 73 ≤ 90, **drop** ✅ |
| Sharp Claw | 9 | 99 | — |
| Rare Wolf Gem | 1 | 100 | — |

→ **Wolf Pelt drops**


### No-drop Example — explicit empty-item entry

The runtime (`weighted_pick` → `rng.choices`) normalizes weights, so a
short-sum table does **not** produce a no-drop chance — it just rebases
the existing entries. To express "no drop" use an explicit entry with an
empty `item:`. The drop resolver in `engine/battle/battle_rewards.py`
skips empty-item picks.

| Item | Weight | Cumulative | Result |
|---|---|---|---|
| Wolf Fang | 60 | 60 | drops on roll ≤ 60 |
| Wolf Pelt | 20 | 80 | drops on 60 < roll ≤ 80 |
| _(no drop)_ — `item: ""` | 20 | 100 | nothing drops on roll > 80 |

Convention: keep the weight total = 100 so percentages read cleanly in
the YAML.

## Updated MC Drop by Zone:

| Zone | Common MC | Rare MC | Boss MC |
|---|---|---|---|
| 1–2 | XS ×3 | S ×1 | S ×2, M ×1 |
| 3–4 | XS ×2, S ×1 | S ×2 | M ×2, L ×1 |
| 5–6 | S ×2 | M ×1 | L ×1, XL ×1 |
| 7–8 | S ×1, M ×1 | M ×2 | L ×2, XL ×1 |
| 9 | M ×2 | L ×1 | L ×2, XL ×2 |
| 10 (final) | M ×2 | L ×1 | L ×3, XL ×3 |
