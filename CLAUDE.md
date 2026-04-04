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
cd tests/tools && ./validate.py
```

Pytest is configured in `pyproject.toml` with `-v -x` (verbose, stop on first failure). Test paths: `tests/` and `engine/`.

## Architecture

### Engine (`engine/`)
- **`main.py`** — Entry point. Parses `--scenario` arg, creates `Injector` with `AppModule`, runs `Game`.
- **`core/app_module.py`** — Central DI wiring. All singletons (scenes, state, loaders) are registered here via `injector` `@provider` methods. This is the first place to look when adding a new system or understanding how components connect.
- **`core/game.py`** — Main game loop (Display, FrameClock, SceneManager).
- **`core/scene_manager.py` / `scene_registry.py`** — Scene lifecycle. Scenes are registered by string name (e.g., `"world_map"`, `"title"`, `"battle"`). Registry supports both singletons and factories (lambda-created per use).
- **`core/scenes/`** — Individual scene implementations (world map, battle, dialogue, shops, title, etc.). Each scene handles its own input, update, and draw.
- **`core/state/`** — Game state: `GameStateHolder` holds current state, `GameStateManager` handles save/load. State is split into `MapState`, `PartyState`, `FlagState`, etc.
- **`core/battle/`** — Battle system (combatants, battle state, rewards).
- **`core/dialogue/`** — Dialogue engine, loads YAML dialogue trees.
- **`core/encounter/`** — Random encounter system (enemy loading, encounter resolution).
- **`core/item/`** — Item effect handling.
- **`core/models/`** — Shared data models (Position, SaveSlot, Clock).

### World (`engine/world/`)
- Tile maps via `pytmx` (.tmx format from Tiled editor), player movement, NPC loading/behavior, camera, collision detection, portals, sprite sheets.

### UI (`engine/ui/`)
- Menu rendering system.

### Data Loading (`engine/data/`)
- `ManifestLoader` reads `manifest.yaml` from the scenario and provides paths to all scenario data directories.

### Scenario (`rusted_kingdoms/`)
- `manifest.yaml` — Scenario entry point defining protagonist, start position, flags, and refs to all data directories.
- `data/` — YAML files for characters, classes, dialogue, encounters, enemies, items, maps, party, recipes.
- `assets/` — Sprites, map tilesets (.tmx/.tsx), audio.

### Tests (`tests/`)
- Unit tests mirror the engine structure under `tests/unit/core/` and `tests/unit/world/`.
- Shared fixtures in `tests/conftest.py`.

## Key Patterns

- **Dependency Injection**: All major components are wired through `AppModule`. To add a new system, add a `@provider` method there and inject it where needed.
- **Scene-based architecture**: Game flow is controlled by switching scenes via `SceneManager`. Each scene is self-contained with input/update/draw methods.
- **Engine/Scenario separation**: The engine never hardcodes scenario data. Everything is loaded from the scenario path via `ManifestLoader` and YAML files.
- **State management**: Game state flows through `GameStateHolder` (current runtime state) and `GameStateManager` (persistence to YAML save files).

## Design Documentation

Detailed design docs live in `docs/` covering battle, party, characters, equipment, maps, dialogue, shops, spells, NPCs, save system, and more.
