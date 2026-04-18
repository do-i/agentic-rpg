# Encounter Zone Schema — Full Reference

Encounter zone files live at `rusted_kingdoms/data/encount/<zone_id>.yaml`.
The zone is auto-loaded; the map's TMX layer must be named to match the zone ID so the engine links them.

---

## Full Schema

```yaml
id: forest_deep          # must match filename (without .yaml)
name: Deep Forest
density: 0.15            # 0.0–1.0 probability per step of triggering encounter
background: forest       # optional: background image ID for battle scene

entries:
  - formation: [forest_spider, forest_spider]
    weight: 10
    chase_range: 0        # tiles player must be within to trigger chase; 0 = no chase

  - formation: [wolf_grey]
    weight: 8
    chase_range: 2

  - formation: [forest_spider, wolf_grey]
    weight: 4
    chase_range: 0

boss:
  id: spider_queen
  name: Spider Queen
  once: true             # fight only triggers once
  on_complete:
    set_flag: spider_queen_defeated

barrier_enemies:
  - id: iron_golem
    requires_item: magic_hammer
    blocked_message: "Your weapons bounce off the iron golem!"
```

---

## density Guidelines

| density | Feel |
|---|---|
| 0.05–0.10 | Light (town outskirts, safe roads) |
| 0.10–0.20 | Normal (forests, plains) |
| 0.20–0.35 | Dense (dungeons, dangerous areas) |
| 0.35+ | Very dense (final areas, cursed zones) |

---

## Formation Tips

- Formations are lists of enemy IDs; repeat an ID for multiple of the same enemy.
- Weight is relative across all entries (higher = more frequent).
- Keep 3–6 formations per zone for variety.
- Mix enemy types for tactical variety.

---

## Wiring to a Map

The encounter zone is linked to a map via the TMX tile layer name in Tiled. The layer containing encounter tiles must be named to match the zone ID. No YAML manifest change is needed — the engine reads the layer name at load time.
