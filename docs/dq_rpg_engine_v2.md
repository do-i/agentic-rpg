# Dragon Quest-Style RPG Engine — Project Brainstorm

## Vision

A modular, classic JRPG engine inspired by Dragon Quest (NES/SNES era), designed with a clean separation between **engine core** and **story content**. Stories, worlds, and characters are delivered as self-contained plugins, letting developers (or solo creators) swap narratives without touching engine internals.

**License:** MIT
**Language:** Python 3.11+
**Map Format:** Tiled (.tmx / .tsx)
**Save Format:** YAML

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│              Story Plugin               │
│  (maps, dialogue, quests, items, lore)  │
└────────────────┬────────────────────────┘
                 │ Plugin API
┌────────────────▼────────────────────────┐
│              Engine Core                │
│  battle · movement · UI · save · audio  │
└─────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.11+ | Dataclasses + type hints throughout |
| Renderer | Pygame-CE | Faster, maintained fork of Pygame |
| Map format | Tiled (.tmx / .tsx) via `pytmx` | Full layer + object support |
| Plugin scripting | Python (`RestrictedPython` sandbox) | Native, no FFI needed |
| Config format | YAML (`ruamel.yaml`) | Human-editable, comment-preserving |
| Save format | YAML | Single file per slot, hand-editable |
| Audio | `pygame.mixer` | BGM + SFX, looping support |
| Build / packaging | `pyproject.toml` + `hatch` | PEP 621 compliant |

### Core Dependencies
```toml
[project.dependencies]
pygame-ce = ">=2.4"
pytmx = ">=3.32"
ruamel-yaml = ">=0.18"
RestrictedPython = ">=7.0"
```

---

## Core Engine Modules

### 1. Battle System

Turn-based, command-menu driven (classic DQ style).

**Command menu:** Attack / Spell / Item / Run

**Player Stats:**

| Stat | Key | Role |
|------|-----|------|
| Level | `level` | Gates spells and equipment access |
| Experience | `exp` | Accumulates to trigger level-up |
| Gold | `gold` | Currency for shops |
| Hit Points | `hp` / `hp_max` | Combat survival |
| Magic Points | `mp` / `mp_max` | Spell resource |
| Strength | `str` | Physical attack damage |
| Dexterity | `dex` | Hit rate, crit chance, turn order |
| Constitution | `con` | HP growth per level, poison resistance |
| Intelligence | `int` | Spell damage, MP growth per level |

**Derived values (computed, not stored in save):**
```
physical_dmg  = str + weapon_atk - enemy_def
spell_dmg     = int * spell_coeff - enemy_mres
hit_chance    = base_hit + (dex * 0.5)
crit_chance   = min(dex * 0.02, 0.25)
turn_order    = dex  (higher dex acts first)
hp_per_level  = con // 3 + class_base
mp_per_level  = int // 4 + class_base
```

**Level-up table format** (per class, defined in plugin):
```yaml
# classes/hero.yaml
class: hero
base_hp: 20
base_mp: 8
stat_growth:
  str:  [2, 2, 3, 2, 3, 2, 3, 3, 2, 3]   # per level 1..N
  dex:  [1, 2, 1, 2, 2, 1, 2, 2, 2, 2]
  con:  [2, 2, 2, 3, 2, 2, 3, 2, 2, 3]
  int:  [1, 1, 1, 1, 2, 1, 1, 2, 1, 2]
exp_curve: quadratic     # linear | quadratic | custom
exp_base: 100
exp_factor: 2.0
```

**Status Effects:** poison, sleep, paralysis, confusion, blind
**Enemy AI tiers:** random, weighted-random, pattern, scripted (boss)
**Elemental affinities:** fire, ice, lightning, holy, dark (resistances per enemy)

---

### 2. World & Map Engine

- Tiled `.tmx` maps loaded via `pytmx`
- Layer types: Ground, Object, Collision, Event, Overhead
- Overworld + sub-maps (towns, dungeons) with separate tilesets
- Tile size: 16×16 or 32×32 (configured per plugin)
- Random encounter zones: `encounter_rate` set as Tiled object property
- NPC system: proximity + talk-to triggers, state-driven dialogue
- Warp/door transitions between maps with fade effect
- Camera: player-centered with map boundary clamping

**Tiled object properties used by engine:**

| Property | Type | Purpose |
|----------|------|---------|
| `encounter_rate` | float | Steps-per-encounter probability |
| `encounter_group` | string | Enemy group table key |
| `warp_target` | string | `map_id:x:y` destination |
| `npc_id` | string | Links object to dialogue script |
| `trigger_flag` | string | Flag to set on step/enter |
| `chest_item` | string | `item_id:qty` |

---

### 3. Dialogue & Script System

- DQ-style bordered text box (bottom of screen)
- Line-by-line rendering with optional name tag
- Script DSL in YAML — readable by non-programmers
- Branching via `choices`, conditional via `if_flag` / `if_gold`
- Localization: string table per `lang/` directory

```yaml
# dialogue/innkeeper.yaml
npc_id: innkeeper_lumis
lines:
  - text: "Welcome, traveler. Rest costs 10 gold."
    choices:
      - label: "Yes please"
        if_gold: 10
        action: rest
        then:
          - text: "Sleep well!"
      - label: "No thanks"
        then:
          - text: "Come back anytime."
  - if_flag: quest_lumis_done
    text: "The village is safe thanks to you!"
```

---

### 4. Quest & Flag System

- Global flag store: `dict[str, bool | int]`
- Quest stages: `NOT_STARTED → ACTIVE → COMPLETE → FAILED`
- Triggers: map enter, NPC talk, flag change, item pickup, battle end
- Plugin hooks for custom conditions (Python, sandboxed)

---

### 5. Inventory & Equipment

- Item types: `Consumable`, `Weapon`, `Armor`, `KeyItem`, `Misc`
- Equipment slots: Weapon, Shield, Helmet, Body, Accessory
- Stat deltas on equip/unequip (`str_bonus`, `def_bonus`, `mres_bonus`, etc.)
- Shop system: buy/sell with gold check
- Item use callbacks: heal, apply status, trigger flag, start cutscene

```yaml
# items/herb.yaml
id: herb
name: Medicinal Herb
type: Consumable
price: 8
effect:
  heal_hp: 30
description: "Restores 30 HP to one ally."
```

### 6. Save System

- 3 save slots (configurable)
- One YAML file per slot: `saves/slot_{n}.yaml`
- Serializes: player stats, inventory, equipment, flags, quest state, map position, playtime, timestamp
- Auto-save at inn rest and map transitions (configurable)
- `schema_version` field enables forward migration

```yaml
# saves/slot_1.yaml
schema_version: 1
plugin: echoes_of_alindra
timestamp: "2026-02-27T14:32:00"
playtime_seconds: 3721
player:
  name: Aldric
  level: 5
  exp: 480
  gold: 230
  hp: 82
  hp_max: 95
  mp: 24
  mp_max: 30
  str: 14
  dex: 11
  con: 13
  int: 9
  equipment:
    weapon: iron_sword
    shield: leather_shield
    helmet: none
    body: chain_mail
    accessory: none
  inventory:
    - {id: herb, qty: 4}
    - {id: antidote, qty: 2}
    - {id: key_lumis_gate, qty: 1}
position:
  map: overworld
  x: 18
  y: 24
flags:
  met_elder: true
  quest_lumis: ACTIVE
  lumis_gate_open: false
  dungeon_b2_visited: false
```

### 7. Audio System

- BGM channels: `overworld`, `dungeon`, `battle`, `town`, `boss`, `cutscene`
- SFX events: attack, spell cast, level up, chest open, menu select, game over
- Plugin declares asset paths in `plugin.yaml`; engine handles all playback
- Loop points supported via metadata sidecar `.loop` file (start/end sample offsets)


### 8. UI / HUD

- DQ-style bordered windows (configurable border tileset per plugin)
- Status HUD: HP/MP displayed as `current/max` numbers (or bar, togglable)
- Main menu: Items / Equipment / Spells / Status / Save / Settings
- Battle UI: command menu + enemy name + animated HP drain
- Mini-map overlay (optional, togglable per plugin)
- Font: bitmap pixel font renderer (plugin can supply custom font sheet)

## Plugin API (Story Package)

A story plugin is a directory (or ZIP) with the following layout:

```
my-story/
├── plugin.yaml          # Metadata + engine config
├── maps/                # Tiled .tmx maps + .tsx tilesets
├── dialogue/            # YAML dialogue scripts per NPC/event
├── quests/              # YAML quest definitions
├── items/               # YAML item definitions
├── enemies/             # YAML enemy stat sheets + AI config
├── spells/              # YAML spell definitions
├── classes/             # YAML class definitions + level-up tables
├── audio/               # BGM (.ogg) and SFX (.wav / .ogg)
├── sprites/             # Tilesets, character sprites, enemy sprites
├── lang/                # Localization string tables (en.yaml, ja.yaml, ...)
└── scripts/             # Optional Python hooks (RestrictedPython sandbox)
```

### plugin.yaml
```yaml
plugin:
  name: "Echoes of Alindra"
  id: echoes_of_alindra
  version: "1.0.0"
  engine_min_version: "0.5.0"
  author: "Your Name"
  license: MIT

engine:
  tile_size: 16
  start_map: overworld
  start_position: [12, 8]
  player_class: hero
  default_lang: en
```

### Python Hook Points (Engine Events)

```python
# scripts/hooks.py  — runs inside RestrictedPython sandbox

def on_map_enter(ctx, map_id: str): ...
def on_battle_end(ctx, result: str): ...      # "win" | "flee" | "lose"
def on_level_up(ctx, new_level: int): ...
def on_item_use(ctx, item_id: str): ...
def on_flag_change(ctx, flag: str, value): ...
def on_npc_talk(ctx, npc_id: str): ...
def on_boss_defeat(ctx, boss_id: str): ...
```

`ctx` exposes a safe read/write API: `ctx.flags`, `ctx.player`, `ctx.give_item()`, `ctx.start_dialogue()`, `ctx.warp()`. Direct engine internals are not accessible.

---

## Project Structure (Engine Repo)

```
dqengine/
├── LICENSE              # MIT
├── README.md
├── pyproject.toml
├── dqengine/
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── engine.py        # Game loop, state machine
│   ├── battle/
│   │   ├── system.py    # Turn logic, damage formulas
│   │   ├── ai.py        # Enemy AI tiers
│   │   └── effects.py   # Status effects
│   ├── world/
│   │   ├── map.py       # pytmx loader + camera
│   │   ├── entity.py    # Player, NPC base classes
│   │   └── encounter.py # Random encounter logic
│   ├── dialogue/
│   │   ├── parser.py    # YAML DSL parser
│   │   └── renderer.py  # Text box renderer
│   ├── inventory/
│   │   ├── items.py
│   │   └── equipment.py
│   ├── save/
│   │   └── manager.py   # YAML read/write + schema migration
│   ├── plugin/
│   │   ├── loader.py    # Plugin discovery + validation
│   │   └── sandbox.py   # RestrictedPython hook runner
│   ├── audio/
│   │   └── manager.py
│   └── ui/
│       ├── window.py    # Bordered window primitive
│       ├── menu.py      # Cursor-based menu widget
│       └── hud.py       # HUD overlay
└── tests/
    ├── test_battle.py
    ├── test_save.py
    └── test_plugin.py
```

---

## Development Phases

### Phase 0 — Engine Skeleton
- [ ] Pygame-CE window + game loop
- [ ] `pytmx` tilemap renderer (Ground + Collision layers)
- [ ] 4-directional player movement with tile collision
- [ ] Camera follow with boundary clamping

### Phase 1 — Core Systems
- [ ] Player stat model + derived value calculations
- [ ] Turn-based battle engine (solo vs. single enemy)
- [ ] YAML dialogue parser + DQ-style text box renderer
- [ ] Inventory + item use
- [ ] YAML save/load (3-slot system)

### Phase 2 — Plugin API
- [ ] `plugin.yaml` loader + schema validation
- [ ] Asset pipeline (load all assets from plugin directory)
- [ ] Flag system + quest stage machine
- [ ] Python hook sandbox (`RestrictedPython`)
- [ ] NPC state machine + dialogue triggers

### Phase 3 — Polish
- [ ] Full party support (1–4 members)
- [ ] Spell system + MP cost
- [ ] Status effects (poison, sleep, paralysis, confusion, blind)
- [ ] Enemy AI patterns + scripted boss logic
- [ ] Shop UI
- [ ] Audio integration (BGM crossfade, SFX event bus)
- [ ] Elemental affinity + resistance system

### Phase 4 — Tooling & Release
- [ ] Tiled workflow documentation + example map
- [ ] Plugin template generator (`dqengine new-plugin`)
- [ ] Plugin validator CLI (`dqengine validate ./my-story`)
- [ ] Demo story plugin (bundled with engine)
- [ ] PyPI package publish

---

## Design Principles

- **Engine knows nothing about story** — zero hardcoded plot, names, or world data in core
- **Data-driven** — all stats, spells, enemies, items in YAML; no magic constants in Python code
- **YAML-first** — save files and configs are human-readable and hand-editable by design
- **Deterministic battle** — seeded `random.Random` instance; reproducible replays and testable
- **Plugin safety** — `RestrictedPython` sandbox; hooks cannot import `os`, `sys`, or mutate engine internals
- **Tiled-native** — engine is a first-class consumer of Tiled's object model; no proprietary map format
- **MIT throughout** — engine, demo plugin, and tooling all MIT licensed

---

## Stretch Goals

- Multiplayer co-op battle (2-player local, shared screen)
- Procedural dungeon generator as optional engine module
- Web-based story editor (Flask/HTMX — no-code dialogue + quest builder)
- Plugin marketplace / community story repository
- Web export via Pygbag (WebAssembly Python + Pygame)

---

## Open Questions

1. **Party size** — Start solo (DQ1 style) and expand to 4? Solo simplifies Phase 1 battle logic significantly.
2. **Resolution lock** — Pin to 320×240 (NES DQ scale) or leave resolution configurable per plugin?
3. **Save migration** — `schema_version` field in YAML enables forward migration; implement migrator in Phase 2.
4. **Tiled version target** — Confirm `pytmx` compatibility with Tiled 1.10+ (both JSON and XML map formats).

---

*Last updated: 2026-02-27*
