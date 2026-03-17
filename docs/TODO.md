# Design Gap Audit

## V1 Suggested Engine Build Order

| Phase | Deliverable | Playable? |
|---|---|---|
| 1 | Boot → load manifest → world map render + player movement | Walk around |
| 2 | Town entry → NPC interaction → dialogue engine | Talk to NPCs |
| 3 | Flag system + save/load | Persist state |
| 4 | Random encounter → battle system → exp/loot | Fight enemies |
| 5 | Party join flow | Full party |
| 6 | Shop + Apothecary | Buy/craft |
| 7 | Boss encounters + story act transitions | Story progression |
| 8 | Full playthrough pass | End-to-end |

### Next Step

Quick summary of where we left off so we can pick up cleanly:

## Sprite Generation

**Core Prompt**

```markdown
Create a pixel-art sprite sheet for a top-down RPG.

STYLE:
- retro fantasy, dark medieval (fits “Rusted Kingdoms” tone)
- consistent pixel art, clean outlines, limited palette (3–6 colors)
- no anti-aliasing, crisp pixels
- transparent background

SPRITE SPECS:
- resolution: 32x32 pixels per frame
- grid layout sprite sheet
- evenly spaced frames

CHARACTER:
- [describe character clearly: e.g., "undead knight with rusted armor and glowing red eyes"]
- silhouette must be readable at small scale

ANIMATIONS:
- idle (2–4 frames)
- walk cycle (4 frames per direction)
- directions: north, south, east, west
- optional: attack (4 frames), death (3 frames)

CONSISTENCY:
- same character across all frames
- consistent proportions, colors, and perspective
- no morphing or style drift

OUTPUT:
- single spritesheet PNG
- grid-aligned frames
- game-ready asset (no extra padding, no background)
```

**Higher-Quality Variant**

```markdown
pixel art sprite sheet, 2D top-down RPG character,
[character description],

32x32 per frame, strict grid layout,
4-directional (N,S,E,W),
idle + walk cycle,

retro gameboy style palette,
hard edges, no blur, no gradients,
consistent character design across frames,

spritesheet layout, evenly spaced tiles,
transparent background,
game-ready asset

IMPORTANT:
no painterly style, no smooth shading, no 3D, no realism
```

```markdown
Create a pixel-art sprite sheet for a top-down RPG.

Character: rusted skeletal knight wearing broken armor, glowing green eyes, carrying a chipped sword.

Style:
- dark fantasy
- retro pixel art
- limited palette (5 colors)
- sharp edges
- no anti-aliasing

Specs:
- 32x32 per frame
- grid-aligned spritesheet
- transparent background

Animations:
- idle (4 frames)
- walk (2 frames per direction)
- directions: north, south, east, west

Constraints:
- consistent character design across all frames
- readable silhouette at small size
- no style drift, no blur, no gradients

Output: clean PNG spritesheet, game-ready.
```

## Next session starting point

**Problem to solve:** `SceneRegistry` stays generic (`dict[str, Scene]`), `AppModule` owns all construction knowledge.

**Direction:**
- `AppModule` registers scenes into `SceneRegistry` — singletons as instances, transients as lambdas/factories
- `SceneRegistry` just stores and returns, no type knowledge
- Scenes receive `SceneManager` + `SceneRegistry`, switch via `registry.get("name")`

**Files that will change:**
- `engine/core/scene_registry.py` — new
- `engine/core/app_module.py` — registers scenes
- `boot_scene.py`, `title_scene.py`, `name_entry_scene.py` — use registry to switch


## V2 Note (for the docs)

> In V2, the engine will accept a `--scenario` launch argument pointing to an external `story_content/` path. For V1, `story_content/` is embedded in the repo and the path is hardcoded in the engine.

Worth logging this now so the engine src doesn't get too tightly coupled to the embedded path when we write it. A single `SCENARIO_ROOT` constant in the engine will make V2 easy to wire up.