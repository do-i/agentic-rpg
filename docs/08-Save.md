# Save Game State

Slot count: 100
Autosave: before/after entering safe area
save state: character status, party repo, location on map
data schema: YAML. file name `YYYY-MM-DD-HH-MM-SS-[CRC32 Hash].yaml`.


## Schema

```yaml
# 2024-03-15-14-22-10-A3F2C1B4.yaml

meta:
  timestamp: "2024-03-15-14-22-10"
  playtime_seconds: 367200        # display as 04d 06h 00m
  location_display: "Town of Ardel"
  is_autosave: false

party:
  - id: hero_aric
    protagonist: true
    name: "Aric"
    class: hero
    level: 8
    exp: 6200
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
    abilities_unlocked: [power_strike, rally]
    status_effects:
      - effect: poison
        duration_turns: 6000 # avoid null. Just put unrealistically long duration

  - id: sera
    protagonist: false
    name: "Sera"
    class: sorcerer
    level: 7
    exp: 5400
    hp: 38
    hp_max: 38
    mp: 52
    mp_max: 60
    str: 8
    dex: 14
    con: 9
    int: 22
    equipped:
      weapon: staff_oak
      shield: none
      helmet: circlet_silver
      body: robe_silk
      accessory: none
    abilities_unlocked: [fire_bolt, aqua_shot]
    status_effects: []

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
  # used for warp destination option
  visited:
    - town_01
    - zone_01_starting_forest
```

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
