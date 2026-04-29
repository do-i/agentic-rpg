# Save Game State

Slot count: 100 player slots + 1 autosave (slot 0)
Autosave: before/after entering safe area
save state: character status, party repo, location on map, opened item boxes
data schema: YAML. File names are slot-indexed: `{slot:03d}.yaml`
(`000.yaml` = autosave, `001.yaml` … `100.yaml` = player slots).
Integrity is protected by a CRC32 `checksum` field embedded inside the YAML
(not in the filename).


## Schema

```yaml
# saves/008.yaml — slot 8

meta:
  timestamp: "2024-03-15-14-22-10"  # %Y-%m-%d-%H-%M-%S
  playtime_seconds: 367200          # display as 04d 06h 00m
  location_display: "Town of Ardel"
  is_autosave: false

party:
  - id: aric
    protagonist: true
    name: "Aric"
    class: hero
    level: 8
    exp: 6200
    exp_next: 17321        # cached threshold for next level
    hp: 55
    hp_max: 68
    mp: 32
    mp_max: 40
    str: 24
    dex: 18
    con: 20
    int: 12
    equipped:
      weapon: iron_sword
      shield: kite_shield
      helmet: iron_helm
      body: chainmail
      accessory: stealth_cloak

party_repository:
  gp: 3200
  items:
    - id: potion
      qty: 5
      tags: [consumable, battle]
      locked: false
    - id: elixir
      qty: 1
      tags: [consumable, battle, rare]
      locked: true

flags:
  - story_quest_started
  - boss_zone01_defeated
  - npc_elder_reward_given

map:
  current: town_01
  position: [12, 8]
  visited:                  # set of map ids ever entered (for future warp use)
    - town_01
    - zone_01_starting_forest

opened_boxes:               # field item-box ids already looted
  - town_01_chest_01

checksum: "A3F2C1B4"        # CRC32 over the rest of the file
```

### Fields not currently persisted

These are intentionally omitted by `engine/io/save_manager.py::_serialize`:

| Field | Reason |
|---|---|
| `abilities_unlocked` | Recomputed from `class` + `level` on load — no need to store |
| `status_effects` | Cleared on save (party rests when saving in safe areas) |

## Playtime Tracking

```yaml
meta:
  playtime_seconds: 367200
```

| Field | Type | Notes |
|---|---|---|
| `playtime_seconds` | int | Cumulative, never resets |
| Session start | datetime | In-memory only, not saved |

### How It Works

- On game load → record `session_start = now()`
- On save → `playtime_seconds += (now() - session_start).seconds; session_start = now()`
- On quit without save → discard session delta

### Display Format

```python
def format_playtime(seconds: int) -> str:
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    return f"{d:02d}d {h:02d}h {m:02d}m"
# 367200 → "04d 06h 00m"
```

### Where Displayed

| Location | Format |
|---|---|
| Save slot list | `04d 06h 00m` |
| Pause menu / title | Same |
