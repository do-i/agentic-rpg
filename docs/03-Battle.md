# 3. Battle System

Turn-based, command-menu driven

**Command menu:** Attack / Spell / Item / Run

**Derived values (computed, not stored in save):**
```
physical_dmg  = str + weapon_atk - enemy_def
spell_dmg     = int * spell_coeff - enemy_mres
hit_chance    = base_hit + (dex * 0.5)
crit_chance   = min(dex * 0.02, 0.25)
turn_order    = dex  (higher dex acts first)
hp_per_level  = con // 3 + class_base
mp_per_level  = int // 4 + class_base
```

## Encounter

Typical encounter

```yaml
encounter_rate: 0.15             # required — drives the roll
encounter_group: forest_enemies  # required — enemy pool or specific boss
once: false                      # optional, default false
```

Boss Event Encount

```yaml
encounter_rate: 1.0             # required — always 100%
encounter_group: boss_001       # required — enemy pool or specific boss
once: true                      # optional, default false
on_complete:                    # optional, omit if no hooks
  set_flag: boss_dragon_defeated
  start_dialogue: elder_aftermath
```


## Post-Battle Rewards

| Reward | Rule |
|---|---|
| **EXP** | Always; split equally among living members |
| **Magic Core (MC)** | Always; minimum 1 guaranteed |
| **Items** | Random chance; 0 or more |
