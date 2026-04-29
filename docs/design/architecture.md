# Retro Style RPG Engine

## Vision

A modular, classic JRPG engine inspired by Dragon Quest (NES/SNES era), designed with a clean separation between **engine core** and **story content**. Stories, worlds, and characters are delivered as self-contained Scenarios, letting developers (or solo creators) swap narratives without touching engine internals.

**License:** MIT
**Language:** Python 3.11+
**Map Format:** Tiled (.tmx / .tsx)
**Save Format:** YAML

## Architecture Overview


┌─────────────────────────────────────────┐
│              Story Scenario             │
│  (maps, dialogue, quests, items, lore)  │
└────────────────┬────────────────────────┘
                 │ Scenario API
┌────────────────▼────────────────────────┐
│              Engine Core                │
│  battle · movement · UI · save · audio  │
└─────────────────────────────────────────┘

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.11+ | Dataclasses + type hints throughout |
| Renderer | Pygame-CE | Faster, maintained fork of Pygame |
| Map format | Tiled (.tmx / .tsx) via `pytmx` | Full layer + object support |
| Scenario scripting | Python (`RestrictedPython` sandbox) | Native, no FFI needed |
| Config format | YAML (`ruamel.yaml`) | Human-editable, comment-preserving |
| Save format | YAML | Single file per slot, hand-editable |
| Audio | `pygame.mixer` | BGM + SFX, looping support |
| Build / packaging | `pyproject.toml` + `hatch` | PEP 621 compliant |

## Sprite Generation

https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/

### Party

See 02-Characters

### NPC
- old_man_01: https://liberatedpixelcup.github.io/Universal-LPC-Spritesheet-Character-Generator/#sex=male&body=Body_Color_light&head=Human_Male_light&expression=Neutral_light&vest=Vest_open_walnut&clothes=TShirt_tan&legs=Cuffed_Pants_walnut&hair=Balding_chestnut&shoes=Basic_Shoes_steel
