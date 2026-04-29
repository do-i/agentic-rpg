# 15. Transportation

## Unlock & Usage Rules

| Mode | Unlock | Usable From | Restriction |
|---|---|---|---|
| Walk | default | anywhere | land tiles only |
| Sail | `transport_sail_unlocked` | port tiles only | water tiles only |
| Fly | `transport_fly_unlocked` | anywhere on world map | skips all terrain |
| Warp | `transport_warp_unlocked` | anywhere on world map | visited locations only |

## Map Config
See `map/world.yaml`

## Notes
- No encounter while flying or sailing
- Warp destinations limited to previously visited towns/dungeons — no spoilers
- Port tiles defined per map config
- Walk remains only mode inside dungeons

## Transportation Unlock Design

| Mode | Trigger | Flag Set | Notes |
|---|---|---|---|
| Sail | Talk to port master NPC (town_port) | `transport_sail_unlocked` | Natural — you hire a ship |
| Fly | Receive `sky_crystal` key item (story reward) | `transport_fly_unlocked` | Boss drop or chest |
| Warp | Story cutscene after Act 3 | `transport_warp_unlocked` | Feels like a late-game power |

## Config Sketch
See `map/town_port.yaml` and `dialogue/port_master_intro.yaml`

## Warp — Destination Rules

Already defined: visited locations only. Worth confirming:

- Warp list = towns + dungeon entrances visited (not interior dungeon tiles)
- No warp inside dungeons — walk only (already in doc 15)

### Warp Ability

```yaml
transport:
  warp:
    unlock_flag: transport_warp_unlocked
    use_context: [world_map, dungeon]
    origin: anywhere
    destinations: visited_only

```