# 15. Transportation

## Unlock & Usage Rules

| Mode | Unlock | Usable From | Restriction |
|---|---|---|---|
| Walk | default | anywhere | land tiles only |
| Sail | `transport_sail_unlocked` | port tiles only | water tiles only |
| Fly | `transport_fly_unlocked` | anywhere on world map | skips all terrain |
| Warp | `transport_warp_unlocked` | anywhere on world map | visited locations only |

## Map Config
```yaml
# map/world.yaml
transport:
  sail:
    unlock_flag: transport_sail_unlocked
    origin: port_tile
  fly:
    unlock_flag: transport_fly_unlocked
    origin: world_map_any
  warp:
    unlock_flag: transport_warp_unlocked
    origin: world_map_any
    destinations: visited_only
```

## Notes
- No encounter while flying or sailing
- Warp destinations limited to previously visited towns/dungeons — no spoilers
- Port tiles defined per map config
- Walk remains only mode inside dungeons
