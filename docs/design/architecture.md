# Retro Style RPG Engine

## Vision

A modular, classic JRPG engine inspired by Dragon Quest (NES/SNES era), designed with a clean separation between **engine core** and **story content**. Stories, worlds, and characters are delivered as self-contained Scenarios, letting developers (or solo creators) swap narratives without touching engine internals.

**License:** MIT
**Language:** Python 3.14+
**Map Format:** Tiled (.tmx / .tsx)
**Save Format:** YAML

## Architecture Overview


┌─────────────────────────────────────────┐
│              Story Scenario             │
│  (maps, dialogue, quests, items, lore)  │
│        — pure YAML / TMX data —         │
└────────────────┬────────────────────────┘
                 │ Manifest + data refs
┌────────────────▼────────────────────────┐
│              Engine Core                │
│  battle · movement · UI · save · audio  │
└─────────────────────────────────────────┘

Scenarios are pure data. There is no scripting sandbox; behavior is wired via
flag-driven YAML (dialogue, encounters, shops, recipes).

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.14+ | Dataclasses + type hints throughout |
| Renderer | Pygame 2.6.x (vanilla) | `pygame==2.6.1` pinned in `pyproject.toml` |
| DI | `injector` | All wiring via `engine/app_module.py` |
| Map format | Tiled (.tmx / .tsx) via `pytmx` | Full layer + object support |
| Scenario format | YAML (`PyYAML`) | Pure data; no scripting sandbox |
| Save format | YAML | One file per slot (`{slot:03d}.yaml`), hand-editable |
| Audio | `pygame.mixer` | BGM + SFX, looping support |
| Build / packaging | `pyproject.toml` + `setuptools` | PEP 621 compliant |
| Test runner | `pytest` | `addopts = -v -x` |

## Sprite Generation

https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/

### Party

See 02-Characters

### NPC
- old_man_01: https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=male&body=Body_Color_light&head=Human_Male_light&expression=Neutral_light&vest=Vest_open_walnut&clothes=TShirt_tan&legs=Cuffed_Pants_walnut&hair=Balding_chestnut&shoes=Basic_Shoes_steel
