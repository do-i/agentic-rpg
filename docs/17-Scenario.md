# 17. Scenario Manifest

## Schema

```
scenario/
├── manifest.yaml # entry point — this doc
├── classes/
│   ├── hero.yaml
│   ├── warrior.yaml
│   ├── mage.yaml
│   ├── cleric.yaml
│   └── rogue.yaml
├── dialogue/
│   └── elder_intro.yaml
├── maps/
│   ├── world.yaml
│   └── town_01.yaml
├── items/
│   └── elixir.yaml
├── enemies/
│   └── forest_wolf.yaml
└── loot/
    └── forest_enemies.yaml
```

## manifest.yaml

```yaml
# manifest.yaml
id: my_rpg_story
name: "Chronicles of the Lost Flame"
version: "1.0.0"

protagonist:
  id: hero_aric
  name: "Aric"  # player-renameable in New Game flow
  class: hero
  sprite: sprites/hero.png

party:
  members:
    - id: sera
      name: "Sera"
      class: sorcerer
      join_condition: story_quest_started   # joins immediately
      join_map: town_01
      join_position: [10, 6]

    - id: kael
      name: "Kael"
      class: warrior
      join_condition: story_act2_started
      join_map: town_02
      join_position: [8, 4]

    - id: lira
      name: "Lira"
      class: cleric
      join_condition: story_act3_started
      join_map: dungeon_03
      join_position: [5, 9]

    - id: zeph
      name: "Zeph"
      class: rogue
      join_condition: story_act4_started
      join_map: port_town
      join_position: [3, 7]

start:
  map: town_01
  position: [12, 8]

bootstrap_flags:
  - story_quest_started

refs:
  classes:   classes/
  maps:      maps/
  dialogue:  dialogue/
  items:     items/
  enemies:   enemies/
  loot:      loot/
```

## Key Design Points

| Decision | Rule |
|---|---|
| One protagonist per scenario | Fixed — no multi-hero support in V1 |
| Protagonist name | Default from manifest, player can rename at New Game |
| Party join order | Driven by `join_condition` flag — story-gated |
| Last member join | Must be enforced at 10–15% story remaining (per `01-Party.md`) |
| `refs` block | Tells engine where to find each subsystem's files |
| Flag IDs | All flags used across all files must be unique — manifest is source of truth |