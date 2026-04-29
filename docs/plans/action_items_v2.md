# Action Items — v2

Self-contained tasks deferred until v1 is fully playable end-to-end.

Status legend: 🟥 not started · 🟨 in progress · 🟩 done · ❓ decision needed

---

## 1. 🟥 Transportation system

`docs/design/transportation.md` defines three unlock flags
(`transport_sail_unlocked`, `transport_fly_unlocked`,
`transport_warp_unlocked`) and rules (land/water tile, visited-only warp,
no dungeon warp). Engine ships nothing: no transport scene, no
`port_tiles` config, no `world.yaml` overworld registry, and
`MapState.visited` is collected but never read.

Out of scope for v1; do not start until the v1 scenario is fully playable.

### Scope when picked up

**Data**
- Per-map `port_tiles: [[x, y], ...]` for sail embark/disembark.
- New `data/maps/world.yaml` master overworld registry: `id`, `name`,
  `position`, `type` (town|dungeon|port), `warp_target` position.

**State**
- New `engine/world/visited_locations.py` (set of map IDs); update from
  `WorldMapScene` on map transition; serialize via `GameStateLoader`.

**Logic** (`engine/world/transport_logic.py`)
- `available_modes(state, map_id, tile)` — filter by flags + tile +
  current map (dungeon → walk only).
- `warp_destinations(state)` — visited towns / dungeon entrances only.
- `can_embark(state, tile)` — sail requires port tile.

**UI**
- Field-menu "Transport" entry, shown only when at least one mode
  beyond walk is unlocked.
- `engine/world/warp_scene.py` — pick visited destination, teleport.
- Sail: trigger on port-tile interact; water-only movement, encounters
  off, re-dock at another port tile.
- Fly: overworld-only mode toggle; flies over anything, encounters off,
  lands on any land tile.

**Integration**
- `EncounterManager` respects `no_encounter` while flying/sailing.
- `PlayerController` gains a second movement mode with distinct
  collision rules per mode.

### Open questions

- Sail/fly sprite art — palette swap or proper boat/aircraft frames?
- Dungeon entrances as warp destinations — confirm by listing every map
  in `world.yaml` with its warp target.
- Warp UX from inside a dungeon — `transportation.md` says warp is
  usable from dungeon *and* world but also lists "Walk remains only
  mode inside dungeons." Resolve before implementing.

---

## 2. 🟥 Field-accessible recipe book

The apothecary NPC remains the only place crafting actually happens. A
read-only field recipe book that lets the player recall already-unlocked
recipes is nice-to-have. A Field Menu slot is already reserved, so wiring
is cheap when picked up.

---

## 3. 🟥 Battle hit-effects polish

`BattleFx` ships a white flash + hurt shake on every damaging hit;
floating damage numbers were already on `BattleState.damage_floats`.
Possible next steps:

- Element / action-type decals (slash, fire puff, ice shards, thunder)
  over the target, keyed off the same action switch
  `SfxManager.play_battle_action` uses.
- Red flash for physical vs white for magic, or crit-only brighter
  flash + 2× shake.
- Damage-number upgrades: "MISS" text, crit flair, bigger font for crits.
- Death fade/dissolve on 0 HP instead of the instant alpha=80 on KO.
- Status-inflict ping overlay when a debuff applies (e.g. green wisp
  for poison).
