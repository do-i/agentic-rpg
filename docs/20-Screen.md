# 20. Screen Design

## World Map / Field

```
┌─────────────────────────────────────┐
│                                     │
│         [Tile Map Viewport]         │
│                                     │
│    ▲  Town ◆  Dungeon ●             │
│         [Player Sprite]             │
│                                     │
│                                     │
└─────────────────────────────────────┘
```
- Slight overhead tile grid, player centered
- Towns/dungeons as visible landmarks
- Minimap optional (modern twist candidate)

---

## Dialogue Box

```
┌─────────────────────────────────────┐
│                                     │
│         [Tile Map — dimmed]         │
│                                     │
├───────┬─────────────────────────────┤
│ [NPC  │ "The forest to the north    │
│  Face]│  has not always been        │
│       │  so dark."                  │
│       │                         ▼   │
└───────┴─────────────────────────────┘
```
- Bottom ~25% of screen
- Portrait left, text right
- `▼` indicator for more text
- Subtle scanline or pixel border (modern twist)

---

## Battle Screen

```
┌─────────────────────────────────────┐
│                                     │
│         [Enemy Sprite(s)]           │
│         centered, large             │
│                                     │
├─────────────────────────────────────┤
│ HP ████████░░  MP ████░░░░          │
│ [Aric]  [Elise]  [Reiya]  [Kael]    │
├─────────────────────────────────────┤
│ > Attack                            │
│   Spell                             │
│   Item                              │
│   Run                               │
└─────────────────────────────────────┘
```
- Top ~50% — enemy sprite(s), background scene
- Middle strip — party HP/MP bars + portraits
- Bottom — command menu, active member highlighted
- Damage numbers float up (modern twist)

---

## Status / Party Screen

```
┌─────────────────────────────────────┐
│ PARTY                    GP 12,400  │
├────────┬────────────────────────────┤
│ [Face] │ Aric        Lv 12  Hero    │
│        │ HP  220/220  MP  80/100    │
│        │ EXP  14,200 / 17,321       │
│        │ STR 18  DEX 14  CON 16     │
├────────┼────────────────────────────┤
│ [Face] │ Elise       Lv 11  Cleric  │
│        │ HP  180/180  MP 120/140    │
│        │ EXP  14,200 / 17,321       │
│        │ STR  8  DEX 10  CON 14     │
└────────┴────────────────────────────┘
```
---

##  Screen

┌─────────────────────────────────────┐
│ EQUIPMENT        [◄ Aric ►]         │
├────────┬────────────────────────────┤
│ [Face] │ Weapon    Iron Sword       │
│        │ Shield    Iron Shield      │
│        │ Helmet    Iron Helm        │
│        │ Body      Chainmail        │
│        │ Accessory —                │
├────────┴────────────────────────────┤
│ STR 18→22  DEF 12→15                │
│ [Item List to equip]                │
└─────────────────────────────────────┘

- ◄ ► to cycle party members
- Stat diff shown when hovering an item (→)
- Only equippable items shown per class


## Item Screen

```
┌─────────────────────────────────────┐
│ ITEMS                    GP 12,400  │
├──────────────────────┬──────────────┤
│ Potion          ×  5 │              │
│ Hi-Potion       ×  3 │ Restores     │
│ Antidote        ×  2 │ 100 HP to    │
│ Echo Herb       ×  1 │ one ally.    │
│ Tent            ×  1 │              │
│                      │ [Use]        │
│                      │ [Discard]    │
└──────────────────────┴──────────────┘
```
- Left — scrollable item list with quantity
- Right — description + actions
- Filter tabs: All / Recovery / Status / Battle / Key
- Use context-aware — grayed out if not usable in current context (field vs battle)

## Menu Navigation (modern twist)

```
┌──────────────┐
│ > Status     │
│   Equipment  │
│   Items      │
│   Apothecary │
│   Save       │
│   Quit       │
└──────────────┘
```
- Opens with ESC or M
- Slides in from left (smooth animation)
- Darkens background

## Modern Twist Candidates

| Element | Idea |
|---|---|
| Damage numbers | Float + fade animation |
| Dialogue | Typewriter text effect |
| Map | Subtle animated water/grass tiles |
| Transitions | Smooth fade in/out between scenes |
| Battle entry | Screen flash + zoom on enemy |
| Level up | Particle burst effect |
| Minimap | Small corner overlay on world map |

---

Before we go further — three decisions:

- **Resolution** — 320×240 scaled ×3 (960×720) for that chunky retro pixel feel, or 1280×720 native?
- **Font** — pixel bitmap font, or modern clean font at small size?
- **Portrait style** — pixel art busts, or do you have something else in mind?

## Tile Map Pipeline
Good choices. Here's the rendering architecture that follows from those decisions:

## Tile Map Pipeline

```
Tiled (.tmx)
  → parser extracts layers + tilesets
  → engine builds layer render queue
  → pygame renders bottom → mid → top per frame
```

The engine needs a **TMX parser** — use `pytmx` library, well-maintained and pygame-friendly.

---

## Layer Model

| Layer | Content | Z-order |
|---|---|---|
| `ground` | grass, water, sand, floor | 0 |
| `mid` | buildings, trees, rocks, NPCs, PC | 1 |
| `top` | weather effects, particles, shadows | 2 |
| `ui` | HUD, dialogue, menus | 3 |

Mid layer needs **Y-sort** — entities lower on screen draw on top of entities higher up. Gives the slight overhead depth illusion.

---

## Sprite Sheet Layout

8 frames, 4 directions — standard RPG layout:

```
      [0]  [1]        ← walk frame A, walk frame B
Down   □    □
Left   □    □
Right  □    □
Up     □    □
```

So each character sheet = 4 rows × 2 cols minimum. With idle frame:

```
        [idle] [walk A] [walk B]
Down      □       □       □
Left      □       □       □
Right     □       □       □
Up        □       □       □
```

4 rows × 3 cols = 12 frames per sheet.

---

## Sprite Renderer Responsibilities

```
SpriteSheet
  └── loads image, slices into frames by row/col

AnimationController
  └── tracks current direction + frame index
  └── advances frame on timer tick

EntityRenderer
  └── gets current frame from AnimationController
  └── passes to mid-layer render queue with y-sort key
```

---

## Camera

- World is larger than viewport (1280×720)
- Camera follows player, clamped to map bounds
- Tiles outside viewport culled — only visible tiles rendered

```python
# Without clamp — camera blindly follows player
camera_x = player_x - screen_width / 2   # can go negative

# With hard clamp — camera stops at map boundaries
camera_x = clamp(
    player_x - screen_width / 2,
    min = 0,                              # left edge
    max = map_width - screen_width        # right edge
)
```
---

## Decisions to confirm

| Item | Proposal |
|---|---|
| TMX parser | `pytmx` |
| Tile size | 32×32 |
| Sprite frame size | matches tile size? |
| Y-sort | by entity bottom edge |
| Camera | player-centered, hard clamp |
| Pygame display | `pygame.SCALED` flag for clean pixel scaling |
