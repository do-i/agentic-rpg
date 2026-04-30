# Action Items v1 — Maps to Create (by Author)

Derived from `docs/scenario/high-level.md`. Status reflects what currently exists under
`rusted_kingdoms/assets/maps/` (`.tmx`) and `rusted_kingdoms/data/maps/` (`.yaml`).

Legend: ✅ tmx + yaml present · 🟡 yaml stub only (needs tmx) · ❌ missing entirely

---

## Act I

### Sub-Epic 1 — The Ember That Would Not Die (Ardel + Starting Forest)

- ✅ `town_01_ardel` — farming town at forest edge; opening scene, burning shrine event
- ✅ `town_01_ardel_house_01` — Aric's home / village elder interior (revelation scene)
- ✅ `town_01_ardel_inn_01` — village inn
- ✅ `town_01_ardel_shop_01` — village smithy/general store
- ✅ `zone_01_starting_forest` — rusted-overnight forest, first Rustkin horde
- ❌ `town_01_ardel_shrine` — burnt shrine interior (post-flare); needed for epilogue camera shot referenced in §8

### Sub-Epic 2 — The Scholar and the Soldier (Millhaven + Open Plains)

- 🟡 `town_02_millhaven` — mill-and-market town; needs tmx
- ❌ `town_02_millhaven_mill` — interior of the failing-fragment mill (Jep confrontation, fragment lost)
- ❌ `town_02_millhaven_inn` — standard town interior set
- ❌ `town_02_millhaven_shop` — standard town interior set
- ✅ `zone_02_open_plains` — road between Millhaven and the coast
- ✅ `zone_02_open_plains_cave_01` — minor side dungeon already present
- ✅ `sample_dungeon_01` — repurpose or retire (currently unscoped to scenario)

---

## Act II

### Sub-Epic 3 — The Port of Half-Truths (Harborgate)

- 🟡 `port_town_harborgate` — free port, quarantined; needs tmx
- ❌ `port_town_harborgate_quarantine` — Reiya tending the sick (named-NPC scene)
- ❌ `port_town_harborgate_harbormaster` — guild HQ, conspiracy reveal
- ❌ `port_town_harborgate_inn` / `_shop` — town interior set
- ❌ `zone_03_coast_road` — connector from Open Plains to Harborgate (optional but expected)

### Sub-Epic 4 — The Watcher on the Ruin (Ruinwatch)

- 🟡 `town_03_ruinwatch` — cliffside town in the bones of a dead monastery; needs tmx
- ❌ `town_03_ruinwatch_monastery_vaults` — Cinder Marshal ambush; first major dungeon set-piece
- ❌ `town_03_ruinwatch_inn` / `_shop` — town interior set
- ❌ `zone_04_cliff_road` — approach to Ruinwatch

---

## Act III

### Sub-Epic 5 — The Kingdom Beneath the Frost (Frostholm)

- 🟡 `town_04_frostholm` — frozen-in-time mountain kingdom; needs tmx (distinct tileset: ice/marble palette)
- ❌ `town_04_frostholm_palace` — eternal court, king's offer scene
- ❌ `town_04_frostholm_vault` — royal vault holding the third Vessel-flame
- ❌ `town_04_frostholm_inn` / `_shop` — town interior set
- ❌ `zone_05_frost_pass` — mountain approach

### Sub-Epic 6 — The Veil of Ash (Ashenveil)

- 🟡 `town_05_ashenveil` — city of mourners on the old capital ruins; needs tmx
- ❌ `town_05_ashenveil_oracle_sanctum` — first Vessel reveal; pivotal exposition scene
- ❌ `town_05_ashenveil_inn` / `_shop` — town interior set
- ❌ `zone_06_ash_road` — approach through the rusted heartlands

---

## Act IV / Finale

### Sub-Epic 7 — The Marshal's Last Stand

- ❌ `zone_07_rusted_wastes` — rusted approach to the final zone
- ❌ `zone_07_marshal_camp` — battlefield-graveyard arena; dialogue-heavy boss map

### Sub-Epic 8 — The Hearth at the End of the World

- ❌ `zone_10_hearth_descent_01` — first floor of the memory-dungeon (Ardel re-enactment)
- ❌ `zone_10_hearth_descent_02` — Millhaven memory floor
- ❌ `zone_10_hearth_descent_03` — Harborgate memory floor
- ❌ `zone_10_hearth_descent_04` — Ruinwatch memory floor
- ❌ `zone_10_hearth_descent_05` — Frostholm memory floor
- ❌ `zone_10_hearth_descent_06` — Ashenveil memory floor
- ❌ `zone_10_hearth_core` — Compact arena (final boss; shape varies by ending path)
- ❌ `town_01_ardel_epilogue` — epilogue variants of Ardel/shrine for the three endings (rebuilt / not / differently)

---

## Cross-Cutting Notes

- **Tilesets needed beyond current set:** rusted-forest variant, port/dock, cliffside monastery, frozen palace, ash/ruin city, rusted-wasteland, abstract "memory" interior tileset for Zone 10.
- **Town interior convention:** every settlement currently uses the Ardel pattern (`<town>_inn_01`, `<town>_shop_01`, plus story-specific houses). Apply the same to Millhaven → Ashenveil to unblock shop/inn/dialogue authoring.
- **Priority ordering for production:** finish Act I/II tmx work first (Millhaven, Harborgate, Ruinwatch already have yaml), then tilesets for Frostholm/Ashenveil (new palettes), then the Zone 10 memory-floor set last (it can reuse earlier tilesets by design).
- **Naming gap:** the high-level doc calls the final area "Zone 10" but Acts III–IV currently jump from `zone_02` to that label. Either renumber (`zone_03`…`zone_09`) per arc, or keep `zone_10_*` as a deliberate gap representing the buried capital.
