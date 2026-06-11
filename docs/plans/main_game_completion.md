# Main Game Completion — Where the Work Is

A standing assessment of what the *main game* needs most, plus a phased,
session-sized task plan. Written 2026-06-11.

## Status (updated 2026-06-11, after the build-out session)

Done: **N1** (see `docs/scenario/zone_map.md` — Q-NUM answered: ids kept,
already contiguous 01–10), **S1**, **S2/S3** (full sprite coverage confirmed,
comments fixed), **Phase A** (Millhaven connected + mill/shop/inn; Ardel
shrine; Harborgate built), **Phase B** at placeholder fidelity (Ruinwatch +
monastery vaults, Frostholm + palace/vault, Ashenveil + oracle sanctum — all
reuse existing tilesets pending Q-ART), and **Phase C partially** (zones
07–10 exist as retargeted copies of earlier zone maps; the campaign-end flag
`boss_zone10_defeated` is reachable, so the game is completable start to
finish). Latent bugs fixed along the way: missing zone_02/zone_03 boss
spawns, cave_01 exit softlock, broken Frostholm/Ashenveil portals.

Remaining: themed tileset passes for all placeholder maps (Q-ART — still the
open decision), `zone_09_marshal_camp` set-piece, the six hearth-descent
memory floors + `zone_10_hearth_core`, the three-variant Ardel epilogue, and
the boss-name / companion-location prose drift listed in `zone_map.md`.

## TL;DR

The **engine is not the bottleneck** — 1266 tests pass, `validate.py` reports
PASS (no broken links, no orphan/undefined flags), and all 20+ subsystems
(battle, shops, equipment, spells, crafting, save/load, dialogue, encounters)
are wired and tested. The bottleneck is the **scenario content layer**: getting
from "engine that works" to "a game you can play start to finish."

Two problems, in priority order:

1. **Three divergent zone-naming systems** that have drifted apart. This is a
   correctness/maintainability problem and should be fixed *before* authoring
   more content, or the drift compounds.
2. **Acts II–IV are largely unbuilt** — many towns are YAML stubs with no
   `.tmx`, the major dungeon set-pieces don't exist, and encounter zones
   `07`–`10` have balance data but no maps to play them in.

Everything else (battle FX polish, transportation system, field recipe book)
is genuinely optional and already captured in `action_items_v2.md`.

---

## The naming-drift problem (fix first)

Three artifacts describe the same journey with three different zone vocabularies:

| Layer | Vocabulary |
|---|---|
| Story (`docs/scenario/high-level.md`) | Ardel → Millhaven → Harborgate → Ruinwatch → Frostholm → Ashenveil → Rusted Wastes → Hearth (zone 10) |
| Maps (`assets/maps/*.tmx`, `data/maps/*.yaml`) | `zone_01_starting_forest`, `zone_02_open_plains`, `zone_03_marshland`, `zone_04_ancient_ruins_*`, `zone_05_mountain_foothills_*`, `zone_06_mountain_pass_*` |
| Encounters (`data/encount/zone_*.yaml`) | `zone_03_marshland`, `zone_04_ancient_ruins`, `zone_07_sunken_cave`, `zone_08_corrupted_forest`, `zone_09_volcanic_region`, `zone_10_final_stronghold` |

Symptoms:
- Encounter zones exist for `zone_07`–`zone_10` (sunken cave, corrupted forest,
  volcanic, final stronghold) but **no maps exist** to host those encounters.
- Town dialogue files reference scenes (`frostholm_captain_hint`,
  `ashenveil_oracle_hint`, `ruinwatch_scholar_hint`) whose towns are
  **`.yaml`-stub-only — no `.tmx`**, so the NPCs have nowhere to stand.
- `action_items_v1_by_author.md` already flags the "Naming gap" but no decision
  has been recorded.

**Task N1 — Reconcile the zone map.** Produce one canonical
`docs/scenario/zone_map.md` table: story arc ↔ overworld zone id ↔ town/dungeon
map ids ↔ encounter zone id ↔ tileset needed. Decide the open question from
`action_items_v1_by_author.md`: renumber arcs `zone_03…zone_09` contiguously, OR
keep `zone_10_*` as a deliberate gap for the buried capital. Then rename the
mismatched encounter YAMLs (`zone_07_sunken_cave` etc.) to match the decision.
`validate.py` + the full test suite must stay green after the rename.
*Size: 1 session. No new art.*

---

## Content build-out (the bulk of the work)

Source of truth for what exists vs. missing is
`docs/plans/action_items_v1_by_author.md`. Current playable extent (from portal
graph): Ardel (+ house/inn/shop) → Starting Forest → Open Plains (+ cave) →
Marshland → Ancient Ruins (gate/courtyard/sanctum) → Foothills (×3) →
Mountain Pass (×3), with `town_04_frostholm`/`town_05_ashenveil`/
`town_02_millhaven` reachable as **exterior shells with no interiors**.

Phased so each phase ends at a playable checkpoint.

### Phase A — Finish Act I/II interiors (unblocks dialogue already written)

These towns have exterior `.tmx` + portals but missing interior sets. The
Ardel pattern (`<town>_inn_01`, `<town>_shop_01`, story houses) is the
convention to copy.

- **A1.** `town_02_millhaven` interiors: `_mill` (Jep confrontation, fragment
  lost), `_shop`. (`_inn` tmx already exists.) Wire `jep_join.yaml`.
- **A2.** `town_01_ardel_shrine` interior (burnt shrine, post-flare) — needed
  for the Sub-Epic 1 beat and the §8 epilogue camera shot.
- **A3.** Harborgate interiors: `port_town_harborgate` has yaml; add
  `_quarantine` (Reiya — `reiya_join.yaml`), `_harbormaster` (reveal,
  `port_master_intro.yaml`), `_inn`/`_shop`.
- *Size: ~1 session per town. Reuses existing tilesets.*

### Phase B — Act III/IV dungeon set-pieces (new tilesets)

- **B1.** Ruinwatch + `_monastery_vaults` (Cinder Marshal first ambush; first
  major dungeon set-piece). Tileset: cliffside monastery.
- **B2.** Frostholm + `_palace` (king's offer) + `_vault` (third Vessel-flame).
  Tileset: ice/marble. Wire `frostholm_captain_hint.yaml`.
- **B3.** Ashenveil + `_oracle_sanctum` (first-Vessel reveal). Tileset: ash/ruin.
  Wire `ashenveil_oracle_hint.yaml`.
- *Size: 1–2 sessions each; gated on new tileset art (see open question Q-ART).*

### Phase C — Finale (Zone 10 memory dungeon)

- **C1.** `zone_07_rusted_wastes` + `zone_07_marshal_camp` (dialogue-heavy boss
  arena, Marshal's last stand).
- **C2.** Six memory floors `zone_10_hearth_descent_01..06` (one per arc; by
  design these *reuse* earlier tilesets) + `zone_10_hearth_core` (Compact final
  boss, shape varies by ending path).
- **C3.** `town_01_ardel_epilogue` — three ending variants (rebuilt / not /
  differently).
- *Size: the largest phase; do last, per the author-plan priority ordering.*

---

## Smaller, independent cleanups (any session, low risk)

- **S1.** Stale comment: `engine/field_menu/field_menu_scene.py:4-6` claims
  "Equipment and Spells are shown as disabled placeholders until those systems
  ship" — but both are wired as live `KIND_SCENE_SWITCH` entries (`equip`,
  `spells`) and have passing scene tests. Fix the comment. *5 min.*
- **S2.** Enemy sprite placeholder: `engine/encounter/enemy_sprite.py:33` still
  falls back to a red rect (`ENEMY_COLOR`). Audit which encounter enemies lack
  real sprites and either fill them or confirm the fallback is intentional.
- **S3.** `combatant.py:64` `sprite_id` "placeholder label for now" — confirm it
  resolves to real battler art across the enemy roster.

---

## Explicitly deferred (already tracked — do NOT pull forward)

Captured in `docs/plans/action_items_v2.md`; out of scope until v1 is playable
end-to-end:
- Transportation system (sail/fly/warp) — `MapState.visited` is collected but
  never read; no overworld `world.yaml` registry exists yet.
- Field-accessible recipe book (a Field Menu slot is reserved).
- Battle hit-effect polish (decals, crit flair, death dissolve).

---

## Open questions to resolve before Phase B

- **Q-ART.** New tilesets needed: cliffside monastery, ice/marble palace,
  ash/ruin city, rusted wasteland. Author them, palette-swap existing, or
  source externally? (Blocks B1–B3.)
- **Q-NUM.** Zone renumbering decision from Task N1 (contiguous vs. `zone_10`
  gap) — must be answered first; everything downstream references it.

## Suggested order

`N1` → `S1` (free win) → Phase A → Q-ART/Q-NUM decisions → Phase B → Phase C.
Run `python -m pytest` and `python tools/validate.py --root rusted_kingdoms`
at the end of every session; both are currently green and should stay that way.
