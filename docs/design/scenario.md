# 17. Scenario Manifest

`manifest.yaml` is the entry point for a scenario. The engine loads it via
`ManifestLoader`, then resolves every other file through the `refs:` block.

## Schema

```yaml
id: my_rpg_story                       # unique scenario id
name: "Chronicles of the Lost Flame"
version: "1.0.0"
window_title: "Rusted Kingdoms"        # OS window title

# ── Title screen ───────────────────────────────────────────
title:
  image: assets/images/title_bg/title_lost_flame.webp
  cursor_icon: assets/images/icons/arrow-head-red-right-01.webp

# ── Global font ────────────────────────────────────────────
font:
  path: assets/fonts/Philosopher-Regular.ttf

# ── Per-shop NPC sprite (face) overrides ───────────────────
apothecary:
  sprite: assets/sprites/npc/female_wiz_01.tsx
  icons:
    locked:  assets/images/icons/lock-locked-red-small.webp
    ready:   assets/images/icons/lock-unlocked-green-small.webp
    missing: assets/images/icons/lock-unlocked-yellow-small.webp

inn:
  sprite: assets/sprites/npc/female_blue_01.tsx

item_shop:
  sprite: assets/sprites/npc/teen_halfmessy_01.tsx

item_box:
  sprite: assets/sprites/objects/item_box.tsx

# ── Protagonist ────────────────────────────────────────────
protagonist:
  id: aric
  name: "Aric"                         # default; player can rename
  class: hero
  character: data/characters/aric.yaml
  sprite: assets/sprites/party/01_aric_walk.tsx

# ── New-game spawn ─────────────────────────────────────────
start:
  map: town_01_ardel
  position: [14, 5]
  intro_dialogue: data/dialogue/intro_cutscene.yaml

# ── Flags ──────────────────────────────────────────────────
bootstrap_flags:                       # injected at New Game
  - story_quest_started

engine_managed_flags:                  # see flag.md — engine fires these
  - story_act2_started
  - story_act3_started
  - story_act4_started
  - boss_zone10_defeated

# ── Data refs ──────────────────────────────────────────────
refs:
  party:      data/party.yaml
  characters: data/characters/
  classes:    data/classes/
  maps:       data/maps/
  dialogue:   data/dialogue/
  items:      data/items/
  enemies:    data/enemies/
  encount:    data/encount/
  recipe:     data/recipe/
  balance:    data/balance.yaml
  assets:     assets/
  tmx:        assets/maps/
```


## Key Design Points

| Decision | Rule |
|---|---|
| One protagonist per scenario | Fixed — no multi-hero support in V1 |
| Protagonist name | Default from manifest, player can rename at New Game |
| Party join order | Driven by `join_condition` flag — story-gated |
| Last member join | Must be enforced at 10–15% story remaining (per `party.md`) |
| `refs` block | Tells engine where to find each subsystem's files |
| Flag IDs | All flags used across all files must be unique — manifest is source of truth |
| `engine_managed_flags` | Flags the engine itself sets at story milestones (see `flag.md`) |