# Plan — Item Box (Field Treasure Chest)

Status: Draft · ready to implement

## Intention

Add a new kind of static field object — an **item box / treasure chest** — that
behaves like a stationary NPC: visible on the map, collides with the player,
and on `Enter` opens a modal (overlay scene) showing its loot. Confirming the
modal transfers the loot (items + magic cores) into the party repository and
marks the chest as opened so it can't be looted again. Configuration is
data-driven per map; sprite path is scenario-wide in `manifest.yaml`.

Resolved design decisions:

- **Position**: per-map YAML `position: [x, y]` (authors pick coords from Tiled).
- **Sprite path**: scenario-wide in `manifest.yaml` under `item_box.sprite`.
- **Loot currency**: no GP. Magic cores only (fits MC-shop-only GP model).
- **Opened state**: new `OpenedBoxesState` on `GameState`, keyed `(map_id, box_id)`.
  No `opened_flag` author convention.
- **Collision after opening**: keeps blocking (simpler, visually consistent).
- **Modal dismiss**: Enter loots + closes. No cancel.

---

## Plan

### 1. Data model — `ItemBox` (`engine/world/item_box.py`)

Modeled on `Npc` but trimmed (no wander/step/facing logic):

- Fields: `id`, `tile_x`, `tile_y`, `loot_items: list[(item_id, qty)]`,
  `loot_magic_cores: list[(size, qty)]`, `present_requires/excludes`, `sprite`.
- Methods: `is_present(flags)`, `is_near(pos)`, `collision_rect`,
  `render(screen, offset, opened)`.
- Does **not** own opened-state; callers pass `opened: bool` from
  `OpenedBoxesState.is_opened(map_id, self.id)`.
- Blocks the player in both states (render-time only differs).

### 2. Sprite — `ItemBoxSprite` (`engine/world/item_box_sprite.py`)

NPC sheets are 4-dir × 9-frame, overkill here. Minimal loader for a 2-frame
horizontal sheet:

- Asset (already present): `rusted_kingdoms/assets/sprites/objects/item_box.png`
  + `item_box.tsx` (frames: **closed | opened**).
- API: `.closed() -> Surface`, `.opened() -> Surface`.
- Loaded **once** by `ItemBoxLoader` from the manifest-declared path.

### 3. Loader — `ItemBoxLoader` (`engine/world/item_box_loader.py`)

Parallels `NpcLoader`:

- Constructor reads `manifest.item_box.sprite` and builds a single
  `ItemBoxSprite`; all `ItemBox` instances share it.
- `load_from_map(map_yaml_path) -> list[ItemBox]` reads the `item_boxes:`
  list from the map YAML.

### 4. Opened-state — `OpenedBoxesState` (`engine/common/opened_boxes_state.py`)

```python
class OpenedBoxesState:
    _opened: set[tuple[str, str]]           # (map_id, box_id)
    def is_opened(map_id, box_id) -> bool
    def mark_opened(map_id, box_id) -> None
    def to_list() -> list[str]              # ["map_id:box_id", ...]
    @classmethod from_list(lst) -> "OpenedBoxesState"
```

Wired into `GameState` alongside `flags`, `map`, `party`, `repository`.
Save/load updates in `engine/io/save_manager.py` + `game_state_loader.py` —
missing key defaults to empty set (back-compat for old saves).

### 5. Modal — `ItemBoxScene` (`engine/world/item_box_scene.py`)

Overlay scene like `DialogueScene` (does not replace `WorldMapScene`):

- Renders a panel: "You found:" then each `name ×qty` line — items first,
  then `Magic Core (size) ×qty` lines.
- `Enter` confirms → calls back into world scene with the `ItemBox`; world
  scene applies loot via `RepositoryState.add_item` (for both items and
  `mc_<size>` ids), then `OpenedBoxesState.mark_opened(map_id, box_id)`,
  then closes modal.
- No cancel path.

### 6. Wire-up in `WorldMapScene`

- `_reset_state`: `self._item_boxes: list[ItemBox] = []`,
  `self._item_box_modal: ItemBoxScene | None = None`.
- `_init`: `self._item_boxes = self._item_box_loader.load_from_map(map_yaml_path)`.
- `handle_events` / `update` / `render`: add modal guards alongside
  `_dialogue`, `_save_modal`, etc.
- Collision: extend `npc_rects` composition in `update` to include all
  present boxes (opened or not).
- Interaction: extend `_try_interact` to also scan `item_boxes` (reuse
  proximity + facing logic from `world_map_logic._is_player_facing`). Add
  `try_interact_item_box` helper in `world_map_logic.py` to keep logic out
  of the scene. Already-opened boxes return no interaction.
- Render: pass `opened=state.opened_boxes.is_opened(map_id, box.id)` to
  `ItemBox.render`.

### 7. DI wiring in `engine/app_module.py`

Add an `@provider @singleton` method for `ItemBoxLoader` (takes
`ManifestLoader`). Inject into `WorldMapScene`.

### 8. Configuration file design

**`manifest.yaml`** gains a scenario-wide item-box section:

```yaml
item_box:
  sprite: assets/sprites/objects/item_box.tsx
```

**Per-map YAML** (e.g. `rusted_kingdoms/data/maps/zone_01_starting_forest.yaml`)
gains a top-level list:

```yaml
item_boxes:
  - id: forest_chest_01
    position: [18, 12]
    present:                              # optional, same shape as NPCs
      requires: [story_quest_started]
      excludes: []
    loot:
      items:
        - id: potion
          qty: 2
        - id: antidote
          qty: 1
      magic_cores:
        - size: m
          qty: 3
        - size: s
          qty: 10
```

Conventions:

- `id` must be unique within its map (not globally).
- `items[*].id` must exist in `data/items/*.yaml`.
- `magic_cores[*].size` must be one of `{xs, s, m, l, xl}`; internally mapped
  to `mc_<size>` ids from `magic_cores.yaml`.
- Either `items` or `magic_cores` may be omitted; both empty is allowed but
  flagged by the validator as a warning.

Tileset (already created at
`rusted_kingdoms/assets/sprites/objects/item_box.tsx`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" name="item_box" tilewidth="32" tileheight="32" tilecount="2" columns="2">
 <image source="item_box.png" width="64" height="32"/>
</tileset>
```

### 9. Tests (`tests/unit/world/` + `tests/unit/common/`)

- `test_item_box.py`: presence checks, collision rect, near detection.
- `test_item_box_loader.py`: YAML → `ItemBox` list; optional sections default
  correctly; invalid magic-core size rejected.
- `test_opened_boxes_state.py`: mark/query, round-trip serialization.
- `test_world_map_item_box_integration.py` (light): interaction → modal →
  repository gains items + `mc_<size>` entries → opened-state set →
  second interaction is a no-op.

### 10. Validator extension (`tools/validate.py`)

- Each `item_boxes[*].loot.items[*].id` must exist in item catalog.
- Each `item_boxes[*].loot.magic_cores[*].size` ∈ `{xs, s, m, l, xl}`.
- `id` unique within a map.
- Empty loot → warning.

---

## Next steps

1. `OpenedBoxesState` + save/load round-trip + test.
2. `ItemBoxSprite` → `ItemBox` → `ItemBoxLoader`.
3. `ItemBoxScene` modal.
4. `WorldMapScene` + `world_map_logic` wiring.
5. `manifest.yaml` `item_box.sprite` entry + `AppModule` DI.
6. One test chest in `zone_01_starting_forest.yaml` as smoke test.
7. Validator extension.
