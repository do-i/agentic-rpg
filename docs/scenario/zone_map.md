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

Updated 2026-06-11 after the build-out session: every town and field zone
below now has a tmx and is wired into the world graph. ⚠️ = placeholder
fidelity — functional map reusing an existing layout/tileset, awaiting its
themed art pass (Q-ART).

| Act / Sub-Epic | Story locale | Field-zone maps | Encounter zone(s) | Town & interior maps | Tileset |
|---|---|---|---|---|---|
| I / 1 | Ardel, Starting Forest | `zone_01_starting_forest` ✅ | `zone_01_starting_forest` | `town_01_ardel` ✅, `_house_01` ✅, `_inn_01` ✅, `_shop_01` ✅, `_shrine` ✅ (burnt hall behind the south fence gate) | existing forest + interior |
| I / 2 | Millhaven, Open Plains | `zone_02_open_plains` ✅, `_cave_01` ✅ | `zone_02_open_plains` | `town_02_millhaven` ✅ (now reachable from the plains' west edge), `_inn` ✅, `_mill` ✅, `_shop` ✅ | existing town + interior |
| II / 3 | Harborgate (port, quarantine) | `zone_03_marshland` ✅ | `zone_03_marshland` | `port_town_harborgate` ⚠️, `_quarantine` ✅, `_harbormaster` ✅, `_inn` ✅, `_shop` ✅ | port/dock pass needed |
| II / 4 | Ruinwatch (dead monastery) | `zone_04_ancient_ruins_01_gate` / `_02_courtyard` / `_03_sanctum` ✅ | one per map, same ids | `town_03_ruinwatch` ⚠️ (cliff-stair portal from the ruins gate), `_monastery_vaults` ✅ (Jep lives here), `_inn` ✅, `_shop` ✅ | cliffside-monastery pass needed |
| III / 5 | Frostholm (frozen kingdom) | `zone_05_mountain_foothills` / `_02` / `_03` ✅ | one per map, same ids | `town_04_frostholm` ⚠️, `_palace` ✅ (king's offer), `_vault` ✅ (behind palace stairs), `_inn` ✅, `_shop` ✅ | ice/marble pass needed |
| III / 6 | Ashenveil (city of mourners) | `zone_06_mountain_pass` / `_02` / `_03` ✅ | one per map, same ids | `town_05_ashenveil` ⚠️, `_oracle_sanctum` ✅, `_inn` ✅, `_shop` ✅ | ash/ruin pass needed |
| IV / 7 | Marshal's approach (prose: "Rusted Wastes") | `zone_07_sunken_cave` ⚠️, `zone_08_corrupted_forest` ⚠️, `zone_09_volcanic_region` ⚠️ (gate guard posted), `zone_09_marshal_camp` ❌ | `zone_07_sunken_cave`, `zone_08_corrupted_forest`, `zone_09_volcanic_region` (all live) | — | cave / corrupted forest / volcanic passes needed |
| IV / 8 | The Hearth (prose: "Zone 10") | `zone_10_final_stronghold` ⚠️ (far exit returns to Ardel's shrine gate), `zone_10_hearth_descent_01..06` ❌, `zone_10_hearth_core` ❌ | `zone_10_final_stronghold` (live; `boss_zone10_defeated` reachable); descent floors + core have none by design | `town_01_ardel_epilogue` ❌ | stronghold + reuse of earlier tilesets (by design) |

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

## Drift found during reconciliation (found 2026-06-11; statuses current)

1. ~~**Millhaven is unreachable.**~~ Fixed: `zone_02_open_plains` west edge ↔
   Millhaven's south road.
2. ~~**Broken live portals** to tmx-less Frostholm/Ashenveil.~~ Fixed: both
   towns built (placeholder fidelity). `tools/validate.py` still does not check
   tmx portal targets — a portal-target check remains worth adding.
3. ~~**Orphan encounter file** `zone_04_ancient_ruins.yaml`.~~ Deleted (N1).
4. **Boss-name drift.** `stronghold_gate_guard.yaml` says nothing comes back
   "until the **Flame Dragon** is dead" while gating on `boss_zone09_defeated`,
   whose encounter boss is **Blackhorn Chief** (`wartotaur_warlord_blackhorn_chief`).
   Rename one or the other. Open.
5. **Companion locations.** The story outline places Jep in Millhaven's mill,
   Reiya in Harborgate, Kael in Ruinwatch. Production data places Jep in the
   Ruinwatch monastery vaults, Reiya in Millhaven, Kael in Frostholm — and the
   join dialogues are written for those placements. Production wins; the prose
   in `high-level.md` should be revised to match.
6. **Found during the build-out (all fixed):** `zone_02_open_plains` and
   `zone_03_marshland` defined encounter bosses but had no `boss_enemy` spawn
   object, so `boss_zone02_defeated` (Reiya join + Act III trigger) and
   `boss_zone03_defeated` were unobtainable; `zone_02_open_plains_cave_01` had
   no exit portal (softlock).

## Remaining work (post build-out)

- Themed tileset passes for the ⚠️ placeholder maps (Q-ART): port/dock,
  cliffside monastery, ice/marble, ash/ruin, cave, corrupted forest, volcanic,
  stronghold.
- `zone_09_marshal_camp` set-piece (needs a Cinder-Marshal boss allocation and
  a scripted-battle beat the engine does not yet express in data).
- `zone_10_hearth_descent_01..06`, `zone_10_hearth_core`, and the three-variant
  `town_01_ardel_epilogue` (need ending-path support).
- A validate.py check for tmx portal targets + landing-tile collision (the
  audit script that found items 1, 2, and 6 ran ad hoc this session).
