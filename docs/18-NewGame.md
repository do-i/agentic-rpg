# 18. New Game / Title Screen Flow

## Title Screen

```
┌─────────────────────────┐
│                         │
│    [Game Title Art]     │
│                         │
│      ▶ New Game         │
│        Load Game        │
│        Settings         │
│        Quit             │
│                         │
└─────────────────────────┘
```

- Scenario supplies the title art asset
- `Load Game` grayed out if no save slots exist

---

## New Game Flow

```
[Title Screen]
  └── New Game selected
        ├── 1. Name Entry Screen
        │     ├── Prompt: "Enter your name"
        │     ├── Default: protagonist.name from manifest.yaml
        │     ├── Max length: 12 characters
        │     └── [Confirm] → proceeds
        │
        ├── 2. Inject bootstrap state
        │     ├── flags: [story_quest_started]
        │     ├── party: protagonist only
        │     ├── party_repository: empty
        │     ├── gp: 0
        │     └── save_slot: none (unsaved)
        │
        ├── 3. Opening cutscene
        │     ├── Defined in manifest.yaml → intro_dialogue
        │     ├── Uses standard dialogue engine (no choices)
        │     └── on_complete → transition to starting map
        │
        └── 4. Load starting map
              ├── map: start.map from manifest.yaml
              └── position: start.position from manifest.yaml
```

## Manifest Hook

```yaml
# scenario/manifest.yaml
start:
  map: town_01
  position: [12, 8]
  intro_dialogue: dialogue/intro_cutscene.yaml  # opening sequence

protagonist:
  name: "Aric"          # default name, player can override
  name_max_length: 12
```
## Load Game Flow

```
[Title Screen]
  └── Load Game selected
        ├── Show save slot list (up to 100 slots)
        │     ├── Slot info: date, playtime, location, protagonist name, level
        │     └── Empty slots shown as [--- Empty ---]
        └── [Select Slot] → restore full save state → resume
```

## State Initialized at New Game

| Field | Value |
|---|---|
| `protagonist.name` | Player input |
| `flags` | `[story_quest_started]` |
| `party` | Protagonist only |
| `party_repository` | Empty |
| `gp` | 0 |
| `map` | `start.map` |
| `position` | `start.position` |
| `save_slots` | All empty |
| `playtime` | 0 |

### State Schema

See 08-Save.md