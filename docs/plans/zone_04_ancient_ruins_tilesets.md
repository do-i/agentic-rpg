# Zone 04 Ancient Ruins Tilesets

This note records the selected tileset PNGs to use when creating
`zone_04_ancient_ruins.tmx`.

## Recommended PNGs

### Primary

| PNG | Use |
|---|---|
| `rusted_kingdoms/assets/tilesets/ground/terrain-v7.png` | Base terrain: dirt, cracked stone, mossy stone, grass, water edges. |
| `rusted_kingdoms/assets/tilesets/stone_tile_stares_16x16.png` | Main ruins kit: stone floors, stairs, walls, gates, masonry, architectural pieces. |
| `rusted_kingdoms/assets/tilesets/grass_cave_walls_24x14.png` | Outdoor vegetation, cliffs, grave/stone details, fences, old wall pieces. |

### Strong Optional

| PNG | Use |
|---|---|
| `rusted_kingdoms/assets/tilesets/schwarnhild/tiles-all-32x32.png` | Darker ruined/dungeon-like stone, pits, rough floors. |
| `rusted_kingdoms/assets/tilesets/schwarnhild/stones_col_01.png` | Ruined column pieces. Needs a companion `.tsx` before clean Tiled use. |
| `rusted_kingdoms/assets/tilesets/window_8x6.png` | Temple/chapel fragments, stained glass, plaques, relic walls. |

### Situational

| PNG | Use |
|---|---|
| `rusted_kingdoms/assets/tilesets/schwarnhild/bridges.png` | Broken walkways or bridge crossings. |
| `rusted_kingdoms/assets/tilesets/beeler/grass_water_clif.png` | Partially flooded or cliffside ruins. Use carefully because style may diverge from current zone maps. |

## Avoid By Default

The `rusted_kingdoms/assets/tilesets/astralpixels/*.png` tiles are mostly
interior furniture, kitchen, shelf, window, and wall assets. Avoid them for the
main outdoor Ancient Ruins map unless creating an indoor ruin chamber.

## Current Map Context

Nearby maps already use the core outdoor/stone set:

| Map | Existing tilesets |
|---|---|
| `zone_03_marshland.tmx` | `ground/terrain-v7.tsx`, `grass_cave_walls_24x14.tsx`, `stone_tile_stares_16x16.tsx` |
| `zone_02_open_plains.tmx` | `grass_cave_walls_24x14.tsx`, `icon_table_stage_14x9.tsx`, `ground/terrain-v7.tsx` |
| `zone_02_open_plains_cave_01.tmx` | `schwarnhild/tiles-all-32x32.tsx` |
| `sample_dungeon_01.tmx` | `stone_tile_stares_16x16.tsx`, `grass_cave_walls_24x14.tsx` |

## Tiled Notes

- Prefer existing `.tsx` files when available.
- Add `rusted_kingdoms/assets/tilesets/schwarnhild/stones_col_01.tsx` before
  using `stones_col_01.png` in Tiled.
- Keep the usual layer names: `ground`, `decoration`, `collision`,
  `spawn_tile`, `portals`, and `boss_enemy` when needed.
- Portal progression should connect Marshland to `zone_04_ancient_ruins`, then
  onward toward the Ruinwatch/Frostholm route.
