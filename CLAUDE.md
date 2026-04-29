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
python -m pytest tests/unit/state/test_map_state.py
python -m pytest tests/unit/state/test_map_state.py::TestMoveTo
python -m pytest tests/unit/state/test_map_state.py::TestMoveTo::test_updates_current_and_position

# Suppress RuntimeWarnings
PYTHONWARNINGS="ignore::RuntimeWarning" python -m pytest

# Data validation
python tools/validate.py --root rusted_kingdoms
```

Pytest is configured in `pyproject.toml` with `-v -x` (verbose, stop on first failure). Test paths: `tests/` and `engine/`.

## Architecture

### Engine (`engine/`)

Code is organised by feature. Each subpackage owns its scene, renderer, state,
and logic together (no global `dto/` / `service/` / `ui/` directories).

- **`main.py`** — Entry point. Parses `--scenario` arg, creates `Injector` with `AppModule`, runs `Game`.
- **`app_module.py`** — Central DI wiring. All singletons are registered here via `injector` `@provider` methods. First place to look when adding a new system.
- **`game.py`** — Main game loop (Display, FrameClock, SceneManager).
- **`settings/`** — `Settings` (compile-time: screen size, FPS, tile size, layers), `EngineSettings` (runtime, from `settings/settings.yaml`), `BalanceData` (scenario balance YAML).
- **`scenes/`** — `SceneRegistrar` + `SceneRegistry` (DI-time wiring of all scenes). The `Scene` base class lives in `engine/common/scene/`.
- **`common/`** — Cross-cutting state and shared UI helpers: `GameState`, `GameStateHolder`, `MapState`, `FlagState`, `OpenedBoxesState`, `SaveSlot`, `Scene` base, `MenuPopup`, `MenuRowRenderer`, `ItemSelectionView`, `TargetSelectOverlayRenderer`, `MenuSfxMixin`.
- **`battle/`** — `BattleScene`, `BattleState`, `Combatant`, `action_resolver`, `turn_advance`, reward calculation, post-battle / game-over scenes, enemy AI, renderers.
- **`dialogue/`** — `DialogueEngine` (YAML dialogue tree resolver) + `DialogueScene`.
- **`encounter/`** — Tile-spawner encounter system: `EncounterManager`, `EnemySpawner`, `EncounterZone`, `EncounterResolver`, enemy sprites.
- **`item/`** — `ItemCatalog`, `ItemEntry`, `ItemEffectHandler`, `ItemLogic`, `ItemScene`, plus `MagicCoreCatalog`.
- **`equipment/`** — `EquipScene` + `equipment_logic`.
- **`field_menu/`** — Field/pause menu.
- **`shop/`** — Item shop, magic-core shop, apothecary (crafting) scenes + renderers.
- **`inn/`** — `InnScene` (rest / save).
- **`spell/`** — `SpellScene` + `spell_logic`.
- **`status/`** — Status screen + `StatusLogic` (spell/effect application).
- **`party/`** — `PartyState`, `MemberState`, `RepositoryState` (shared item pool + GP caps).
- **`title/`** — Boot, title, name-entry, load-game, save-modal scenes.
- **`record/`** — Input recording / replay.
- **`audio/`** — `BgmManager`, `SfxManager`.
- **`util/`** — `Clock` protocol, `FrameClock`, `Playtime`, `PseudoRandom`, `WeightedPick`.
- **`io/`** — `ManifestLoader`, `GameStateManager` (save/load), `GameStateLoader` (new-game / save factories), `yaml_loader`.
- **`world/`** — Tile maps via `pytmx`, player movement, NPC, camera, collision, sprite sheets, world-map scene + logic, item-box scene, portals.
- **`debug/`** — Debug bootstrapping.

### Scenario (`rusted_kingdoms/`)
- `manifest.yaml` — Scenario entry point defining protagonist, start position, flags, and refs to all data directories.
- `data/` — YAML files for characters, classes, dialogue, encounters, enemies, items, maps, party, recipes.
- `assets/` — Sprites, map tilesets (.tmx/.tsx), audio.

### Tests (`tests/`)
- Unit tests under `tests/unit/`, organized by subsystem (`battle/`, `dialogue/`, `world/`, `state/`, …).
- Shared fixtures in `tests/conftest.py`.

## Key Patterns

- **Dependency Injection**: All major components are wired through `AppModule`. To add a new system, add a `@provider` method there and inject it where needed.
- **Scene-based architecture**: Game flow is controlled by switching scenes via `SceneManager`. Each scene is self-contained with input/update/draw methods.
- **Engine/Scenario separation**: The engine never hardcodes scenario data. Everything is loaded from the scenario path via `ManifestLoader` and YAML files.
- **State management**: Game state flows through `GameStateHolder` (current runtime state, in `engine/common/`) and `GameStateManager` (in `engine/io/`, handles persistence to YAML save files). Per-feature state lives next to its scene (e.g. `engine/party/`, `engine/item/`).

## Design Documentation

- `docs/design/` — long-lived subsystem references (battle, party, characters, equipment, maps, dialogue, shops, spells, NPCs, save, etc.). See `docs/design/INDEX.md` for the grouped reading order.
- `docs/plans/` — active work-in-progress plans (deleted/archived once done).
- `docs/scenario/` — scenario-specific narrative/design notes (e.g. `rusted_kingdoms` high-level outline).
