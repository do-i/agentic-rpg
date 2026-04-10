# Battle Background Image

The best image size is 1280x720 — that's the exact screen resolution from Settings. Note that only the top
  65% (468px) is visible as the battle area; the bottom 252px is covered by the party/command panel. So compose the
  interesting parts of the art in the upper portion.

## Overview

Add background images to the battle scene. Currently the battle renderer fills the screen with a solid dark color (`C_BG`) and draws a flat floor rectangle. Replace this with per-zone background art.

## Asset Requirements

- Image size: **1280x720** (matches `Settings.SCREEN_WIDTH` x `Settings.SCREEN_HEIGHT`)
- Format: PNG
- Location: `rusted_kingdoms/assets/images/battle_bg/`
- Naming: `<zone_background_id>.png` (e.g., `forest.png`, `cave.png`, `plains.png`)
- The enemy area occupies the top 65% (468px), the bottom panel the rest — compose art with that split in mind

## Code Changes

### 1. Add `background` field to `EncounterZone`

- **File:** `engine/dto/encounter_zone.py`
- Add `background: str = ""` to the `EncounterZone` dataclass

### 2. Parse `background` from zone YAML

- **File:** `engine/encounter/encounter_zone.py` (or `engine/io/encounter_zone_loader.py`)
- Read `background` key from the YAML and pass it into `EncounterZone`

### 3. Carry background ID through to the battle

- **File:** `engine/battle/battle_state.py`
- Add `background: str = ""` field to `BattleState`
- Set it when `EncounterManager` builds the `BattleState` from a zone

### 4. Render the background image

- **File:** `engine/ui/battle_renderer.py`
- Load and cache the background image (scale to screen size if needed)
- Replace `screen.fill(C_BG)` and the floor rect in `render()` / `_draw_enemy_area()` with `screen.blit(bg_image, (0, 0))`
- Fall back to the current solid-color fill when no background is set
