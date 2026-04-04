# Remaining Scene Refactor: Shop Scenes

## Status

The following scene extractions are **complete**:

| Scene | Logic file | Renderer file |
|---|---|---|
| `battle_scene.py` | `battle_logic.py` | `battle_renderer.py` |
| `item_scene.py` | `item_logic.py` | `item_renderer.py` |
| `status_scene.py` | `status_logic.py` | `status_renderer.py` |
| `world_map_scene.py` | `world_map_logic.py` | _(rendering stays — mostly delegation)_ |

## Remaining: Shop Scenes (item_shop + magic_core_shop)

### What to extract

#### `shop_renderer.py` (~250 lines)

Both `item_shop_scene.py` (393 lines) and `magic_core_shop_scene.py` (404 lines) share near-identical rendering patterns:

- Modal background dimming + rounded box
- Header with title + GP display + divider
- Scrollable item list rows (selected highlight, cursor glyph, price/rate)
- Footer with key hints + divider
- Quantity selector overlay (left/right arrows, quantity number, total price)
- Toast message rendering

Unify into a single `ShopRenderer` class with methods like:
- `render_modal_frame(screen, mx, my, mw, mh)`
- `render_header(screen, mx, my, title, gp)`
- `render_list_rows(screen, mx, y, rows, sel, scroll, columns_fn)`
- `render_qty_overlay(screen, mx, my, mw, mh, label, qty, total, hint)`
- `render_toast(screen, text, color)`
- `render_footer(screen, mx, y, hint_text)`

Each shop scene passes a `columns_fn` callback to customize per-row content (item shop shows price + owned count; MC shop shows rate + total GP).

#### `item_shop_logic.py` (~100 lines)

Extract from `item_shop_scene.py`:
- `available(shop_items, flags)` — filter by unlock flags
- `max_buyable(price, owned, gp)` — affordability + cap calculation
- `do_buy(repo, item_id, qty, price, tags)` — execute purchase transaction
- `display_name(item)` — human-readable name

#### `magic_core_shop_logic.py` (~100 lines)

Extract from `magic_core_shop_scene.py`:
- `MC_SIZES` catalog constant
- `LARGE_SIZES` set
- `available(repo)` — owned MC sizes with quantities
- `qty_loop(qty, delta, max_qty)` — wrapping quantity adjustment
- `do_exchange(repo, item_id, qty, rate)` — execute exchange transaction

### Resulting file sizes

| File | Before | After |
|---|---|---|
| `item_shop_scene.py` | 393 | ~150 |
| `magic_core_shop_scene.py` | 404 | ~160 |
| `shop_renderer.py` | _(new)_ | ~250 |
| `item_shop_logic.py` | _(new)_ | ~100 |
| `magic_core_shop_logic.py` | _(new)_ | ~100 |

### How to implement

1. Create `shop_renderer.py` with the shared `ShopRenderer` class
2. Create `item_shop_logic.py` with purchase logic functions
3. Create `magic_core_shop_logic.py` with exchange logic functions
4. Rewrite `item_shop_scene.py` to use `ShopRenderer` + `item_shop_logic`
5. Rewrite `magic_core_shop_scene.py` to use `ShopRenderer` + `magic_core_shop_logic`
6. Add unit tests for both logic modules
7. Verify existing tests still pass

### Why deferred

The two shop scenes are moderately sized (393 and 404 lines) and already have reasonably clean logic/render separation internally. The main win here is **deduplication** of the shared modal rendering, which requires designing a flexible `columns_fn` callback interface. This is a slightly higher-risk change than the mechanical extractions done so far, so it was scoped separately.
