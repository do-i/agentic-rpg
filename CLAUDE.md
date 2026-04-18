# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A modular JRPG engine (Dragon Quest / NES-SNES era) built with Python 3.14, Pygame, and dependency injection via `injector`. The engine is separated from story content — scenarios (like `rusted_kingdoms/`) are self-contained data packages with maps, dialogue, items, enemies, and sprites.

## Commands

```sh
# Setup
python -m venv .venv
source .venv/bin/activate.fish
pip install -e ".[dev]"

# Run the game
python -m engine.main --scenario ./rusted_kingdoms

# Run all tests
python -m pytest

# Run a specific test file / class / test
python -m pytest tests/unit/core/state/test_map_state.py
python -m pytest tests/unit/core/state/test_map_state.py::TestMoveTo
python -m pytest tests/unit/core/state/test_map_state.py::TestMoveTo::test_updates_current_and_position

# Suppress RuntimeWarnings
PYTHONWARNINGS="ignore::RuntimeWarning" python -m pytest

# Data validation
python tools/validate.py --root rusted_kingdoms
```

Pytest is configured in `pyproject.toml` with `-v -x` (verbose, stop on first failure). Test paths: `tests/` and `engine/`.

## Architecture

### Engine (`engine/`)
- **`main.py`** — Entry point. Parses `--scenario` arg, creates `Injector` with `AppModule`, runs `Game`.
- **`app_module.py`** — Central DI wiring. All singletons (scenes, state, loaders) are registered here via `injector` `@provider` methods. This is the first place to look when adding a new system or understanding how components connect.
- **`game.py`** — Main game loop (Display, FrameClock, SceneManager).
- **`settings/`** — `Settings` (compile-time constants: screen size, FPS, tile size, layers) and `EngineSettings` (runtime config loaded from `settings/settings.yaml`).
- **`scenes/`** — Scene base class, `SceneManager`, `SceneRegistry`, and all scene implementations (world map, battle, dialogue, shops, title, etc.). Each scene handles its own input, update, and draw.
- **`battle/`** — Battle system (combatants, battle state, battle logic, reward calculation).
- **`dialogue/`** — Dialogue engine, loads YAML dialogue trees.
- **`encounter/`** — Random encounter system (encounter manager, encounter resolution).
- **`item/`** — Item effect handling and item logic.
- **`service/`** — Business logic services: `RepositoryState` (inventory management, GP caps, sell validation), stat calculation helpers (`calc_exp_next`, `stat_gain_at`, `recalc_exp_next`), `StatusLogic` (spell application).
- **`dto/`** — Data containers: `Position`, `SaveSlot`, `Portal`, `EncounterZone`, `BattleRewards`, `FieldItemDef`, `UseResult`, `FlagState`, `MapState`, `GameState`, `GameStateHolder`, `PartyState`, `MemberState`, `ItemEntry`.
- **`util/`** — Small utilities: `Clock` protocol + implementations, `FrameClock` (pygame timing), `Playtime` (session time accumulator).
- **`io/`** — All file I/O: `ManifestLoader`, `SaveManager`, `EnemyLoader`, `ItemCatalog`, `NpcLoader`, `PortalLoader`, `EncounterZoneLoader`, `GameStateLoader` (new-game/save factories).
- **`debug/`** — Debug bootstrapping.

### UI (`engine/ui/`)
- Display management, menu rendering, and all scene renderers (battle, item, status) and overlays (target select).

### World (`engine/world/`)
- Tile maps via `pytmx` (.tmx format from Tiled editor), player movement, NPC behavior, camera, collision detection, sprite sheets, world map logic.

### Scenario (`rusted_kingdoms/`)
- `manifest.yaml` — Scenario entry point defining protagonist, start position, flags, and refs to all data directories.
- `data/` — YAML files for characters, classes, dialogue, encounters, enemies, items, maps, party, recipes.
- `assets/` — Sprites, map tilesets (.tmx/.tsx), audio.

### Tests (`tests/`)
- Unit tests under `tests/unit/`. Legacy path `tests/unit/core/` still exists pending test directory reorganization.
- Shared fixtures in `tests/conftest.py`.

## Key Patterns

- **Dependency Injection**: All major components are wired through `AppModule`. To add a new system, add a `@provider` method there and inject it where needed.
- **Scene-based architecture**: Game flow is controlled by switching scenes via `SceneManager`. Each scene is self-contained with input/update/draw methods.
- **Engine/Scenario separation**: The engine never hardcodes scenario data. Everything is loaded from the scenario path via `ManifestLoader` and YAML files.
- **State management**: Game state flows through `GameStateHolder` (dto, current runtime state) and `GameStateManager` (io, persistence to YAML save files). Data containers live in `dto/`, business logic in `service/`, and factory/persistence in `io/`.

## Design Documentation

Detailed design docs live in `docs/` covering battle, party, characters, equipment, maps, dialogue, shops, spells, NPCs, save system, and more.
