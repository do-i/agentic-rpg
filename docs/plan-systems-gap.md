# Plan — Fill System Gaps

Remaining gaps after v1 engine work landed. Field Menu, Equipment, Spells, and the v1 Apothecary follow-ups (unique-output guard, `phoenix_wing` data fix) are shipped.

Open items:

1. Crafting — recipe book (v2) + scenario-author wiring of `unlock_flag` chain
2. Fast Travel / Transportation (v2)

---

## 1. Crafting — Apothecary follow-ups

### Remaining gaps

1. **Field-accessible recipe book** (**v2, deferred**) — apothecary NPC remains the only place crafting actually happens; a read-only field recipe book that lets the player recall already-unlocked recipes is nice-to-have but defer until v1 is playable. A Field Menu slot is already reserved so wiring is cheap when picked up.

2. **Recipe unlock story wiring** (scenario authoring, parallel) — the `unlock_flag` chain (`story_quest_started` → `story_act2_started` → ...) must be fired from real NPC dialogue / encounter triggers. This is scenario content work, not engine — flagged here so it's not forgotten. Add NPCs and dialogue branches that set each flag at the right story beat.

### Scope

(1) is deferred. (2) is content, tracked here but owned by the scenario author.

---

## 2. Fast Travel / Transportation — **deferred to v2**

**Status**: v2 / lowest priority. Do not start until v1 scenario is fully authored and the game is playable end-to-end. The sections below are kept as a reference spec for when the feature is picked up.

### Current state

- `docs/15-Transportation.md` defines three unlock flags (`transport_sail_unlocked`, `transport_fly_unlocked`, `transport_warp_unlocked`) and rules (land/water tile, visited-only warp, no dungeon warp).
- No transport scene, no flag wiring, no port tile config, no visited-location registry.

### Gap

Everything: data, state, UI, and world-map collision/movement integration.

### Scope

#### Data

- Extend `map/*.yaml` with a per-map `port_tiles: [[x, y], ...]` list for sail embark/disembark points.
- Add `map/world.yaml` (referenced by doc 15 but does not exist) — master list of overworld locations with `id`, `name`, `position`, `type` (town|dungeon|port), `warp_target` position.

#### State

- New DTO: `engine/dto/visited_locations.py` — set of map IDs the player has entered. Updated in `WorldMapScene` on map transition.
- Save integration: serialize in `GameStateLoader` as `visited: [id, id, ...]`.
- Flag reads: `FlagState` already supports `has_flag(flag_id)`; transport modes just query it.

#### Logic (`engine/service/transport_logic.py`, new)

- `available_modes(state, map_id, tile) -> list[mode]` — filter by flags, current tile type, current map (dungeon = walk only).
- `warp_destinations(state) -> list[location]` — filtered to visited town/dungeon-entrance locations only.
- `can_embark(state, tile) -> bool` — sail requires port tile.

#### UI

- **Field menu entry**: "Transport" option, shown only when at least one mode beyond walk is unlocked.
- **Warp picker**: new `engine/world/warp_scene.py` — list of visited destinations, confirm → teleport player to target map + position.
- **Sail**: trigger on port-tile interact. Switch player sprite/movement rules (water-only), disable encounter table while sailing, re-dock at another port tile.
- **Fly**: overworld-only mode toggle; player flies over anything, encounters off, can land on any land tile.

### Integration points

- `EncounterManager` must respect a `no_encounter: bool` flag while flying/sailing.
- `WorldMapScene.update` must update `visited_locations` on map change.
- Sail/fly need a second movement mode in `PlayerController` (distinct collision rules per mode).

### Open questions

- Sail/fly sprite art — currently single overworld sprite; do we need boat + aircraft frames? Minimum viable: palette-swap or a simple overlay.
- Dungeon entrances as warp destinations — doc 15 says yes (entrance only, not interior). Confirm by listing every map in `map/world.yaml` with its warp target.
- Warp UX from inside a dungeon — doc 15 says warp is usable from dungeon *and* world, but lists "Walk remains only mode inside dungeons" as a contradiction. Clarify before implementing.

---

## Recommended Sequencing

**v2 (post-v1)**

1. **Scenario authoring** (parallel track) — NPCs + dialogue that fire the `story_*` unlock flags the recipe chain depends on.
2. **Field recipe book** — read-only recall of unlocked recipes, as a Field Menu entry.
3. **Transportation** — visited-location state → warp scene → sail/fly movement modes.

Each system should land with tests under `tests/unit/` mirroring the package path.
