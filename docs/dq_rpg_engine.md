# Dragon Quest-Style RPG Engine — Project Brainstorm

## Vision

A modular, classic JRPG engine inspired by Dragon Quest (NES/SNES era), designed with a clean separation between **engine core** and **story content**. Stories, worlds, and characters are delivered as self-contained plugins, letting developers (or solo creators) swap narratives without touching engine internals.

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

## Core Engine Modules

### 1. Battle System
- Turn-based, single-player-character or small-party (1–4)
- Command menu: Attack / Spell / Item / Run
- Stats: HP, MP, ATK, DEF, AGI, LCK
- Elemental affinities (fire, ice, lightning, holy, dark)
- Status effects: poison, sleep, confusion, paralysis
- Enemy AI tiers: random, pattern, scripted boss logic
- Experience & leveling with stat growth curves (configurable per class)

### 2. World & Map Engine
- Tile-based overworld (top-down, 16×16 or 32×32 tiles)
- Town / dungeon sub-maps with separate tilesets
- Random encounter zones with configurable encounter rate tables
- NPC interaction system (proximity trigger, talk-to trigger)
- Warp / door / transition system between maps

### 3. Dialogue & Script System
- Line-by-line dialogue box renderer (DQ-style with name tag optional)
- Branching dialogue via simple script DSL (YAML or TOML-based)
- Conditional flags: `if player.has_item(key)`, `if quest.step == 3`
- Choice menus embedded in dialogue
- Localization-ready (string table per language)

### 4. Quest & Flag System
- Global flag store (boolean + integer variables)
- Quest log with stages: Not Started → Active → Complete
- Event triggers: flag change, map enter, NPC state change
- Plugin hooks for custom trigger conditions

### 5. Inventory & Equipment
- Item types: Consumable, Weapon, Armor, Key Item, Misc
- Equipment slots: Weapon, Shield, Helmet, Armor, Accessory
- Stat modifiers on equip/unequip
- Shop system with buy/sell logic
- Item use callbacks (heal, apply status, trigger cutscene)

### 6. Save System
- Slot-based save (3 slots default, configurable)
- Serialize: player stats, inventory, flags, map position, quest state
- Auto-save checkpoint support
- Save format: JSON or SQLite (swappable backend)

### 7. Audio System
- BGM channels: overworld, dungeon, battle, town, boss
- SFX: attack, spell, menu select, level up, chest open
- Plugin provides audio asset paths; engine handles playback
- Support for looping regions in BGM tracks

### 8. UI / HUD
- Status window (HP/MP bars or number display)
- Menu system: Items / Equipment / Spells / Status / Save / Settings
- Battle command menu with cursor navigation
- Mini-map (optional, togglable)
- Font renderer with DQ-style bordered text boxes

---

## Plugin API (Story Package)

A story plugin is a directory (or ZIP) containing:

```
my-story/
├── plugin.toml          # Metadata: name, version, engine version req
├── maps/                # Tiled-compatible .tmx or custom format
├── dialogue/            # .yaml script files per NPC/event
├── quests/              # Quest definitions
├── items/               # Item definitions
├── enemies/             # Enemy stat sheets + AI hints
├── spells/              # Spell definitions (damage, cost, effect)
├── classes/             # Player class(es) + level-up tables
├── audio/               # BGM and SFX assets (or asset manifest)
├── sprites/             # Tilesets, character sprites, enemy sprites
└── scripts/             # Optional Lua/Python hooks for custom logic
```

### plugin.toml example
```toml
[plugin]
name = "Echoes of Alindra"
version = "1.0.0"
engine_min_version = "0.5.0"
start_map = "overworld"
start_position = [12, 8]
player_class = "hero"
```

### Script Hook Points (Engine Events)
| Hook | Trigger |
|------|---------|
| `on_map_enter(map_id)` | Player enters a new map |
| `on_battle_end(result)` | Battle won/fled/lost |
| `on_level_up(new_level)` | Player levels up |
| `on_item_use(item_id)` | Item used from inventory |
| `on_flag_change(flag, value)` | Any global flag changes |
| `on_npc_talk(npc_id)` | Player initiates NPC dialogue |
| `on_boss_defeat(boss_id)` | Named boss defeated |

---

## Tech Stack Options

| Layer | Option A (Web/Electron) | Option B (Native) |
|-------|------------------------|-------------------|
| Language | TypeScript | Rust / C++ |
| Renderer | Phaser 3 / Pixi.js | SDL2 / Raylib |
| Scripting | JavaScript eval / Duktape | Lua 5.4 |
| Data format | YAML + JSON | TOML + JSON |
| Save | IndexedDB / localStorage | SQLite |
| Build | Vite + Electron | Cargo / CMake |

**Recommended start:** TypeScript + Phaser 3 for fastest iteration, with Lua scripting via a WASM Lua runtime for plugin hooks.

---

## Development Phases

### Phase 0 — Engine Skeleton
- [ ] Tilemap renderer (load Tiled .tmx)
- [ ] Player movement (4-directional, collision)
- [ ] Basic camera follow

### Phase 1 — Core Systems
- [ ] Turn-based battle engine
- [ ] Dialogue box + script interpreter
- [ ] Inventory + item use
- [ ] Save/load system

### Phase 2 — Plugin API
- [ ] Plugin loader (reads `plugin.toml`)
- [ ] Asset pipeline (sprites, audio, maps from plugin dir)
- [ ] Hook/event system for custom scripts
- [ ] Hot-reload support for rapid story development

### Phase 3 — Polish
- [ ] Spell animations
- [ ] Status effect system
- [ ] Shop UI
- [ ] Quest log UI
- [ ] Sound engine integration

### Phase 4 — Tooling
- [ ] Map editor integration (Tiled)
- [ ] Dialogue editor (simple GUI or VS Code extension)
- [ ] Enemy / item data editor
- [ ] Plugin packager / validator CLI

---

## Design Principles

- **Engine knows nothing about story** — zero hardcoded plot, names, or world data in core
- **Data-driven** — stats, spells, enemies defined in config files, not code
- **Deterministic battle** — seed-based RNG for reproducible replays / debugging
- **Minimal dependencies** — easy to build and distribute
- **Plugin safety** — sandboxed script execution; plugins can't break engine state directly

---

## Stretch Goals

- Multiplayer co-op battle (2-player local, shared screen)
- Procedural dungeon generator as optional engine module
- Plugin marketplace / community story repository
- Web-based story editor (no-code dialogue + quest builder)
- Mobile export (touch controls overlay)

---

## Open Questions

1. **Scripting language** — Lua vs. a custom DSL vs. full JS? Lua has the best JRPG precedent (RPG Maker-adjacent).
2. **Art style enforcement** — Should the engine enforce pixel art constraints (palette limits, resolution lock), or leave that fully to plugins?
3. **License** — MIT engine core with separate story plugin licenses, or keep both proprietary?
4. **Save portability** — Should saves be tied to a specific plugin version, or support migration?

---

*Last updated: 2026-02-27*
