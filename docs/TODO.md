## Missing Critical Design Areas

### 🔴 High Priority (Blockers)

| Area | Why Critical |
|---|---|
| **Combat Resolution / Damage Formula** | `physical_dmg = str + weapon_atk - enemy_def` exists, but no floor/ceiling defined — negative damage possible |
| **Status Effect System** | Effects listed (poison, sleep, stun) but no tick timing, stack rules, or interaction with death |
| **Game Over & Retry Flow** | "offer retry from last save" — but no detail on what state is restored, or if mid-dungeon saves exist |
| **Dialogue / Script System** | Flags are referenced everywhere (`set_flag`, `start_dialogue`) but no dialogue data model defined |
| **Flag System** | Central to NPC behavior, building access, recipe unlock, boss events — no schema or lifecycle defined |

### 🟡 Medium Priority (Design Gaps)

| Area | Gap |
|---|---|
| **Mage class** | Docs say Fire/Ice/Wind, but YAML has Fire/Wind/Lightning — no Ice spell |
| **EXP & Level-up trigger** | Formula implied (`exp_base`, `exp_factor`) but level-up event flow not defined |
| **Encounter rate w/ Rogue** | Rogue reduces encounter rate by 15%, but base rate varies per map — interaction unspecified |
| **Shop restock** | Does stock replenish? Infinite or limited supply? |
| **Warp / Transportation unlock** | Fly, sail, warp listed — no unlock conditions or map restrictions |

### 🟢 Nice to Have (Polish)

- **New Game / Title screen flow**
- **Settings** (keybinding, volume placeholders for later BGM)
- **Plugin manifest schema** — protagonist name, party member names are "plugin-defined" but no spec

---

**Suggest tackling in order:** Flag System → Dialogue Model → Status Effect tick rules → Damage floor → Level-up flow