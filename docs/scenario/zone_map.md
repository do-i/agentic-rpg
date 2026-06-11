# Canonical Zone Map — Rusted Kingdoms

Single source of truth reconciling the three vocabularies that drifted apart:
the story outline (`high-level.md`), the map ids (`assets/maps/*.tmx`,
`data/maps/*.yaml`), and the encounter zone ids (`data/encount/*.yaml`).
Written 2026-06-11 (Task N1 of `docs/plans/main_game_completion.md`).

## Decision (Q-NUM)

**Zone ids `zone_01`–`zone_10` are kept exactly as they are.** The numbering is
already contiguous — maps exist for `zone_01`–`zone_06`, and encounter data
exists for `zone_07`–`zone_10`. There is no gap to close and no renumbering to
do. The "Acts III–IV jump from zone_02 to zone_10" concern in
`action_items_v1_by_author.md` predates the zone 03–06 map work and is stale.

Per the author's own cross-cutting note, **the sprite-backed encounter zone ids
are canonical for production**; story prose adapts to them. Concretely:

- The prose "Rusted Wastes / Marshal's camp" (Sub-Epic 7) is realized across
  `zone_07_sunken_cave` → `zone_08_corrupted_forest` → `zone_09_volcanic_region`.
  The Cinder Marshal set-piece is staged on the volcanic approach as
  `zone_09_marshal_camp` (new map id, no new encounter zone — it is a
  dialogue-heavy boss arena).
- The prose "Zone 10 / the Hearth" (Sub-Epic 8) is realized as
  `zone_10_final_stronghold` (exterior approach, hosts the existing encounter
  zone) plus interior memory floors `zone_10_hearth_descent_01..06` and
  `zone_10_hearth_core` (encounter-free by design — the Rustkin there are not
  hostile).

The in-game dialogue already commits to this geography
(`ashenveil_oracle_hint`: Sunken Cave is *below Ashenveil* and blocks the lower
road in Act III; the Corrupted Forest is *west* and gates Act IV;
`stronghold_gate_guard`: the zone_09 boss gates the Final Stronghold). Boss
flags `boss_zone07_defeated` … `boss_zone10_defeated` keep their names.

## Canonical table

Status legend: ✅ tmx + yaml · 🟡 yaml only (needs tmx) · ❌ missing entirely.
"Encounter id" is the filename under `data/encount/` (loaded by map id — a map
without a matching encount file simply has no encounters, which is correct for
towns and interiors).

| Act / Sub-Epic | Story locale | Field-zone maps | Encounter zone(s) | Town & interior maps | Tileset |
|---|---|---|---|---|---|
| I / 1 | Ardel, Starting Forest | `zone_01_starting_forest` ✅ | `zone_01_starting_forest` | `town_01_ardel` ✅, `_house_01` ✅, `_inn_01` ✅, `_shop_01` ✅, `_shrine` ❌ | existing forest + interior |
| I / 2 | Millhaven, Open Plains | `zone_02_open_plains` ✅, `_cave_01` ✅ | `zone_02_open_plains` | `town_02_millhaven` ✅ (tmx exists but **unreachable** — see drift list), `_inn` ✅ tmx (unwired), `_mill` ❌, `_shop` ❌ | existing town + interior |
| II / 3 | Harborgate (port, quarantine) | `zone_03_marshland` ✅ | `zone_03_marshland` | `port_town_harborgate` 🟡, `_quarantine` ❌, `_harbormaster` ❌, `_inn` ❌, `_shop` ❌ | port/dock (needed) |
| II / 4 | Ruinwatch (dead monastery) | `zone_04_ancient_ruins_01_gate` / `_02_courtyard` / `_03_sanctum` ✅ | one per map, same ids | `town_03_ruinwatch` 🟡, `_monastery_vaults` ❌, `_inn` ❌, `_shop` ❌ | cliffside monastery (needed) |
| III / 5 | Frostholm (frozen kingdom) | `zone_05_mountain_foothills` / `_02` / `_03` ✅ | one per map, same ids | `town_04_frostholm` 🟡 (**live portals point here — crash risk**), `_palace` ❌, `_vault` ❌, `_inn` ❌, `_shop` ❌ | ice/marble (needed) |
| III / 6 | Ashenveil (city of mourners) | `zone_06_mountain_pass` / `_02` / `_03` ✅ | one per map, same ids | `town_05_ashenveil` 🟡 (**live portal points here — crash risk**), `_oracle_sanctum` ❌, `_inn` ❌, `_shop` ❌ | ash/ruin (needed) |
| IV / 7 | Marshal's approach (prose: "Rusted Wastes") | `zone_07_sunken_cave` ❌, `zone_08_corrupted_forest` ❌, `zone_09_volcanic_region` ❌, `zone_09_marshal_camp` ❌ | `zone_07_sunken_cave`, `zone_08_corrupted_forest`, `zone_09_volcanic_region` (all data ✅) | — | cave / corrupted forest / volcanic (needed) |
| IV / 8 | The Hearth (prose: "Zone 10") | `zone_10_final_stronghold` ❌, `zone_10_hearth_descent_01..06` ❌, `zone_10_hearth_core` ❌ | `zone_10_final_stronghold` (data ✅); descent floors + core have none by design | `town_01_ardel_epilogue` ❌ | stronghold + reuse of earlier tilesets (by design) |

## Geography / progression spine

```
town_01_ardel ↔ zone_01_starting_forest ↔ zone_02_open_plains (↔ cave_01, ↔ town_02_millhaven*)
  ↔ zone_03_marshland (↔ port_town_harborgate*)
  ↔ zone_04_ancient_ruins 01→02→03 (↔ town_03_ruinwatch*)
  ↔ zone_05_mountain_foothills 01→02→03 ↔ town_04_frostholm*
  ↔ zone_06_mountain_pass 01→02→03 ↔ town_05_ashenveil*
  ↔ zone_07_sunken_cave* ("below" Ashenveil)
  ↔ zone_08_corrupted_forest* ("west")
  ↔ zone_09_volcanic_region* (→ zone_09_marshal_camp*)
  ↔ zone_10_final_stronghold* (→ hearth descent 01..06 → hearth_core*)
```

`*` = link or map does not exist yet.

## Drift found during reconciliation (state as of 2026-06-11)

1. **Millhaven is unreachable.** `town_02_millhaven.tmx` exists and links to its
   inn, but no zone map has a portal into the town. `zone_02_open_plains` needs
   an entry portal. (Fixed in Phase A1.)
2. **Broken live portals.** `zone_05_mountain_foothills_03` and
   `zone_06_mountain_pass` portal to `town_04_frostholm`, and
   `zone_06_mountain_pass_03` portals to `town_05_ashenveil` — neither town has
   a `.tmx`, so traversal crashes. `tools/validate.py` does not check tmx portal
   targets, which is why this never surfaced. (Towns are Phase B; consider a
   validate.py portal-target check.)
3. **Orphan encounter file.** `data/encount/zone_04_ancient_ruins.yaml` is
   loaded by map id, and no map with id `zone_04_ancient_ruins` exists (the
   ruins are split into `_01_gate/_02_courtyard/_03_sanctum`, each with its own
   encount file). Deleted as part of N1.
4. **Boss-name drift.** `stronghold_gate_guard.yaml` says nothing comes back
   "until the **Flame Dragon** is dead" while gating on `boss_zone09_defeated`,
   whose encounter boss is **Blackhorn Chief** (`wartotaur_warlord_blackhorn_chief`).
   Resolve when zone_09 is built (rename one or the other).
5. **Kael's location.** The story outline introduces Kael at Ruinwatch (Act II);
   production dialogue (`frostholm_captain_hint`) places him in Frostholm and
   `kael_join` gates on `boss_zone06_defeated`. Production wins; update the
   prose when Ruinwatch content is authored.
