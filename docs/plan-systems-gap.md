# Plan — Fill System Gaps

Covers four systems the design docs specify but the engine does not yet fully implement:

1. Equipment
2. Spells / Magic menu
3. Crafting (recipe) — **already shipped via Apothecary; only follow-ups remain**
4. Fast Travel / Transportation

Cross-cutting prerequisite: a **Field Menu** (party / status / items / equipment / spells entry point from the world map). Equipment and Spells both need it; building it first avoids two one-off entry points.

Sequencing recommendation (v1): Field Menu → Equipment → Spells. Crafting follow-ups slot in anywhere. **Fast Travel is deferred to v2** — apply it after the v1 scenario is fully authored and playable end-to-end.

---

## 0. Cross-Cutting: Field Menu

### Current state

- `world_map_scene.py` opens scenes directly on tile events (item shop, apothecary, inn, item box, save modal).
- `status_scene.py` and `item_scene.py` exist but have no confirmed field-menu entry point from the world map.
- There is no unified pause menu.

### Gap

A pause/field menu scene that exposes Items, Status, Equipment, Spells, Save, (later) Transport. Without it, Equipment and Spells have no home.

### Scope

- New scene: `engine/world/field_menu_scene.py` (or `engine/common/scene/field_menu_scene.py`).
- Opened on a dedicated key (e.g. `ESC` or `M`) from `WorldMapScene.handle_events`.
- Each entry dispatches to an existing overlay scene via `SceneManager.push`.
- DI: register in `AppModule` as a factory (fresh instance per open).

**v1 entries**: Items, Status, Equipment, Spells, Save.

**v2 entries (deferred)**: Recipe Book (recall unlocked apothecary recipes), Transport. Keep the menu extensible — don't hardcode the v1 entry list; drive it from a list that's easy to append to.

### Open questions

- Key binding: reuse `ESC` (currently closes modals) or new key? Recommend `M` to avoid conflict.
- Should the menu pause world animation? For parity with DQ-era, yes — freeze NPC AI and animation while open.

---

## 1. Equipment

### Current state

- `MemberState.equipped: dict` slot exists (`engine/party/member_state.py:32,49`).
- `rusted_kingdoms/data/classes/*.yaml` defines `equipment_slots` (weapon/shield/helmet/body/accessory) with allowed categories per class.
- `rusted_kingdoms/data/items/accessories.yaml` is the only equipment data that exists. No `weapons.yaml`, `armor.yaml`, `shields.yaml`, `helmets.yaml`.
- `docs/05-Equipment.md` describes the shop Buy/Sell tab flow but not the field-menu equip UI.

### Gap

Three layers missing:

1. **Data**: weapon / shield / helmet / body item YAMLs.
2. **Logic**: equip/unequip service that (a) validates `class_restriction`/`equippable`, (b) swaps repository ↔ `MemberState.equipped`, (c) recomputes derived stats.
3. **UI**: two entry points — shop (Buy/Sell per doc 5) and field menu (re-equip from repository).

### Scope

#### Data (do first; unblocks everything else)

- Create `items/weapons.yaml`, `items/shields.yaml`, `items/helmets.yaml`, `items/body.yaml`.
- Each entry: `id`, `name`, `type` (weapon|shield|helmet|body|accessory), `slot_category` (sword|axe|heavy|light|...), `equippable: [class_ids]` (omit = all), `stats: {str: +X, def: +Y, ...}`, `buy_price`, `sell_price`, `description`.
- Respect the **no hardcoded defaults** rule: every entry must set `buy_price` and `sell_price` explicitly — if `null`, treat as unsellable and document it.
- Update `ManifestLoader` / `ItemCatalog` to load equipment alongside consumables.

#### Logic (`engine/service/equipment_logic.py`, new)

- `can_equip(member, item) -> bool` — checks class restriction + `equipment_slots` category match.
- `equip(member, item) -> unequipped_item | None` — moves item from repository to slot, returns swapped-out item (may be `None`).
- `unequip(member, slot) -> item | None` — moves current to repository.
- `recompute_stats(member)` — applies stat deltas from all equipped items on top of base stats. Call after equip/unequip.
- Save integration: `GameStateLoader` already persists `MemberState.equipped` as a dict; verify round-trip.

#### UI

- **Shop-side (doc 5 Buy/Sell tabs)**: extend/duplicate `ItemShopScene`. The hardest part is the per-character status preview panel (STR 8 → 10▲, grayed = locked). Reuse `ItemSelectionView` if possible.
- **Field-side equip screen**: new `engine/world/equip_scene.py`. Character list → slot list → item picker (filtered by slot category and class restriction) → confirm. Show `before → after` stat diff on focus, same widget as shop preview.

### Integration points

- `BattleState.combatant` must read equipped stat totals, not just base stats. Audit `engine/battle/combatant.py` and `engine/service/` stat helpers.
- `RepositoryState.sell_item` must refuse equipped items (or force unequip first — doc 5 implies sell is from repository only, so equipped items are already protected).

### Open questions

- Stat preview for the "grayed" (class-restricted) state vs the "net-negative" state — doc 5 calls these out as two distinct visual states. Confirm grayscale vs red-minus treatment.
- Accessories already exist (`accessories.yaml`) but have no equip flow. Harmonize with the new item types.
- Starting equipment: where does it come from? Likely `party.yaml` needs an `equipped:` block per member, consumed by `GameStateLoader`.

---

## 2. Spells / Magic menu

### Current state

- `docs/16-Spells.md` is a 14-line stub: just the unlock table (20 spells × 4 elements × 5 tiers). No data, no damage formulae, no targeting rules beyond the table.
- `classes/*.yaml` defines per-class `abilities` (e.g. `hero.yaml`: Power Strike, Rally, War Cry) — these act like spells but are class-specific, not the elemental spell system from doc 16.
- `engine/service/` has `StatusLogic` (applies status effects); no `SpellLogic` yet.
- Battle menu: audit needed — does it already expose class abilities? Likely yes via `hero.yaml.abilities`, since battle works.

### Gap

1. **Design gaps in doc 16** — who learns which spell? Is it class-based (sorcerer gets fire/ice, cleric gets heal) or universal level-gated? Doc 16 says "one unlock per level" which reads universal, but that conflicts with the class `abilities` pattern.
2. **Data**: no `data/spells/` directory; no spell definitions.
3. **Battle integration**: spells must appear in battle command menu with MP cost, target select, and damage resolution.
4. **Field menu integration**: a Spells screen showing learned spells (for inspection / field-cast heals).

### Design decision (locked)

**Spells are a separate axis from class abilities.** Class `abilities:` remain martial (Power Strike, Rally, War Cry). Elemental spells from doc 16 are a second list, gated by a per-class `spell_schools: [fire, water, ...]` attribute. Non-casters (`warrior`, `hero`, `rogue`) get `spell_schools: []`; `sorcerer` and `cleric` get the relevant element lists.

### Scope

#### Data

- New `rusted_kingdoms/data/spells/fire.yaml`, `water.yaml`, `wind.yaml`, `earth.yaml`.
- Per spell: `id`, `name`, `element`, `tier`, `unlock_level`, `mp_cost`, `power` (coeff), `target` (single_enemy / all_enemies / single_ally / all_allies), `status_effect` (optional id).
- Ultimates: `unlock_flag: story_act4_ultimate` per doc 16.
- `classes/*.yaml` gains `spell_schools: [fire, water]` (or `[]` for non-casters) — this is the class gate.

#### Logic (`engine/service/spell_logic.py`, new)

- `learned_spells(member) -> list[spell]` — intersect `member.level` with `spell.unlock_level`, filter by `class.spell_schools`, filter ultimates by `flags`.
- `cast(caster, spell, targets) -> list[SpellResult]` — damage/heal formula, status application, MP deduction.
- Damage formula: reuse `BattleLogic` damage pattern, swap STR for INT.

#### UI

- **Battle**: add `MAGIC` command to battle menu (if not present). Opens a spell list from `learned_spells`. Shares target-select overlay with items.
- **Field**: `engine/world/spell_scene.py` — character → learned spells list. Only field-castable ones (heals, buffs, warp if overloaded) are usable outside battle; others are inspect-only.

### Integration points

- `Combatant` / `BattleState` need to know caster MP and deduct on cast.
- SFX: `SfxManager.play_battle_action` already keys on action type — extend with element keys if per-element SFX is wanted (ties into the `battle_fx` follow-up list in `remaining_refactor.md`).

### Open questions

- MP regen model: do spells consume a shared resource pool, or per-character MP (current `MemberState.mp`)? Current model is per-character; confirm doc 16 matches.
- Doc 16 says "ultimates gated by story flag" (singular) — one flag for all four, or per-element flags? Recommend per-element for pacing.
- Overlap with class abilities: Rally boosts party DEF, so does a (future) earth buff spell. That's fine if named distinctly, but design review the overlap.

---

## 3. Crafting — Apothecary follow-ups

### Current state

**Already shipped**: `engine/shop/apothecary_scene.py`, `all_recipe.yaml`, `ApothecaryRenderer`, lock/unlock icons, detail panel, craft action, GP deduction, repository update. Entry point is `WorldMapScene._open_apothecary` on tile event.

### Remaining gaps

None are blockers. Items ordered by priority for v1:

1. **Key-item duplicate guard** (v1) — `docs/07-Apothecally.md:126` flags `veil_breaker` as qty-1. Audit `apothecary_scene` and enforce:
   - Unique-output recipe is listed normally while the player does not own the output.
   - Once owned, the row stays visible but is **grayed out and non-selectable** (so the player still sees the recipe exists but cannot craft a duplicate).

2. **Drop the "presence-check" input concept** (v1 data fix) — keeping the recipe schema simple (all inputs are consumed). Instead of extending the schema with `consume: false`, **replace `phoenix_wing` in `all_recipe.yaml` with a consumable input of equivalent difficulty/rarity**. Update the recipe and the material/drop tables accordingly.

3. **Field-accessible recipe book** (**v2, deferred**) — apothecary NPC remains the only place crafting actually happens; a read-only field recipe book that lets the player recall already-unlocked recipes is nice-to-have but defer until v1 is playable. Reserve a Field Menu slot for it (see section 0) so wiring is cheap when picked up.

4. **Recipe unlock story wiring** (scenario authoring, parallel) — the `unlock_flag` chain (`story_quest_started` → `story_act2_started` → ...) must be fired from real NPC dialogue / encounter triggers. This is scenario content work, not engine — flagged here so it's not forgotten. Add NPCs and dialogue branches that set each flag at the right story beat.

### Scope

v1 engine work in this section = (1) + (2). Both are surgical. (3) is deferred. (4) is content, tracked here but owned by the scenario author.

---

## 4. Fast Travel / Transportation — **deferred to v2**

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

**v1 (playable game)**

1. **Field Menu** — unblocks Equipment and Spells UI entry. v1 entries: Items / Status / Equipment / Spells / Save.
2. **Equipment** — data → logic → field scene → shop scene. Biggest system, most per-char logic churn.
3. **Apothecary follow-ups** (small task, slot in any time) — unique-output grayed-out guard, `phoenix_wing` data fix.
4. **Spells** — data (Option A schema) → battle integration → field scene.
5. **Scenario authoring** (parallel track) — NPCs + dialogue that fire the `story_*` unlock flags the recipe chain depends on.

**v2 (post-v1)**

6. **Field recipe book** — read-only recall of unlocked recipes, as a Field Menu entry.
7. **Transportation** — visited-location state → warp scene → sail/fly movement modes.

Each system should land with tests under `tests/unit/` mirroring the package path. Scenario content gaps (missing TMX maps, per-tile attribution from `TODO.md`) are orthogonal and can proceed in parallel.
