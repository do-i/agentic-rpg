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


### No-drop Example — weights sum to 80

```
Roll random(1, 100)
If roll > 80 → nothing drops
Otherwise → walk table as normal
```
