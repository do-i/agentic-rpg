# Plan: Load Screen Redesign

## Goal

Replace the dense single-row slot display with a two-row layout.
Repurpose the yellow rect as a selection cursor. Move LATEST to a small pill badge.

---

## Current Layout (one row, 44px tall)

```
▶  Slot 01   Aric  Lv12  04d 06h 00m  Ardel  2026-04-16 10:22   [LATEST]
             ← display_line() crammed into remaining width →
```

- `SLOT_HEIGHT = 44`, `VISIBLE_SLOTS = 10`
- Yellow border rect = most-recent indicator
- `▶` glyph = selection cursor
- Detail text is clipped when LATEST badge is visible

---

## New Layout (two rows, ~64px tall)

```
┌─────────────────────────────────────────────────────────────┐  ← yellow border when selected
│  Slot 01   Aric   Lv 12   Ardel                  ● LATEST  │  ← row 1
│            2026-04-16 10:22   04d 06h 00m                   │  ← row 2
└─────────────────────────────────────────────────────────────┘
```

Column positions (relative to slot left edge `mx + 10`):

| Element          | x offset | row | color (filled) | color (empty) |
|------------------|----------|-----|----------------|---------------|
| Slot label       | +12      | 1   | `(200,200,160)` | `(80,80,70)` |
| Name + Lv        | +110     | 1   | `(240,240,200)` | — |
| Location         | +280     | 1   | `(180,200,160)` | — |
| LATEST pill      | right-aligned, row 1 | — | `(240,200,60)` bg, dark text | — |
| Timestamp        | +110     | 2   | `(140,140,110)` | — |
| Playtime         | +310     | 2   | `(140,140,110)` | — |
| Empty label      | +110     | 1   | `(70,70,60)`    | — |

---

## Constants to Change

| Constant        | Old | New  | Reason |
|-----------------|-----|------|--------|
| `SLOT_HEIGHT`   | 44  | 64   | two text rows + padding |
| `VISIBLE_SLOTS` | 10  | 7    | taller rows, same MODAL_H |
| `MODAL_H`       | 540 | 560  | slight increase to breathe |

`VISIBLE_SLOTS = 7` fits within `MODAL_H = 560`:
- Header + divider: ~70px
- 7 × 64px = 448px
- Hint bar: ~30px
- Total ≈ 548px ✓

---

## Cursor: Yellow Rect (repurposed)

**Before:** yellow `draw.rect(..., width=3)` border drawn only on `most_recent` slot.

**After:** yellow border drawn on the `selected` slot instead.

```python
if selected:
    pygame.draw.rect(screen, (240, 200, 60), (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4), 2)
```

Remove the `▶` glyph — the yellow border is the cursor.

---

## LATEST Pill Badge

Small filled pill (rounded rect) right-aligned in row 1, visible only on `most_recent` slot.

```python
if most_recent:
    badge = font_hint.render("LATEST", True, (20, 20, 40))
    bw, bh = badge.get_size()
    pill_x = mx + MODAL_W - bw - 26
    pill_y = y + (row1_center - bh // 2)
    pygame.draw.rect(screen, (240, 200, 60),
                     (pill_x - 6, pill_y - 3, bw + 12, bh + 6),
                     border_radius=6)
    screen.blit(badge, (pill_x, pill_y))
```

No more full-border yellow rect on most_recent.

---

## `_render_row` Refactor

Replace the current monolithic `_render_row` with explicit row 1 / row 2 draws:

```python
row1_y = y + 8
row2_y = y + 34  # 64px slot → ~26px between baselines

# Background
bg = (38, 38, 68) if selected else (24, 24, 44)
pygame.draw.rect(screen, bg, (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4))

# Cursor (yellow border on selected)
if selected:
    pygame.draw.rect(screen, (240, 200, 60),
                     (mx + 10, y, MODAL_W - 20, SLOT_HEIGHT - 4), 2)

# Slot label (both rows, vertically centered)
label = font_slot.render(slot.label, True, label_col)
screen.blit(label, (mx + 12, y + (SLOT_HEIGHT - 4 - label.get_height()) // 2))

if slot.is_empty:
    empty = font_slot.render("--- Empty ---", True, (70, 70, 60))
    screen.blit(empty, (mx + 110, row1_y))
else:
    # Row 1: Name  Lv N  Location
    name_lv = font_slot.render(f"{slot.protagonist_name}  Lv {slot.level}", True, (240,240,200))
    screen.blit(name_lv, (mx + 110, row1_y))
    loc = font_small.render(slot.location, True, (180, 200, 160))
    screen.blit(loc, (mx + 280, row1_y + 2))   # +2 baseline nudge for smaller font

    # Row 2: Timestamp  Playtime
    ts = font_small.render(slot.timestamp, True, (140, 140, 110))
    screen.blit(ts, (mx + 110, row2_y))
    pt = font_small.render(slot.playtime_display, True, (140, 140, 110))
    screen.blit(pt, (mx + 310, row2_y))

    # LATEST pill
    if most_recent:
        _draw_latest_pill(screen, font_hint, mx, y)
```

---

## Font Changes

Add a third, smaller font for secondary info (row 2 + location):

```python
self._font_title = pygame.font.SysFont("Arial", 32, bold=True)
self._font_slot  = pygame.font.SysFont("Arial", 22)          # row 1 name/level
self._font_small = pygame.font.SysFont("Arial", 17)          # row 2 + location
self._font_hint  = pygame.font.SysFont("Arial", 18)          # hint bar + LATEST
```

---

## `display_line()` in SaveSlot

This method becomes unused by the load screen after the redesign. Leave it in place
(save_modal_scene may still use it), but note it can be removed in a future cleanup.

---

## File Checklist

- [ ] `engine/title/load_game_scene.py` — all rendering changes
- [ ] `docs/plan-load-screen-redesign.md` — this file (delete when done)
