# Action Items — v3: Codebase Refactoring & Improvements

Findings from a full-codebase review (2026-07-02). Ordered by priority:
P1 = architecture/correctness, P2 = duplication & structure, P3 = hygiene.
Each item is self-contained and can be picked up independently.

Status legend: 🟥 not started · 🟨 in progress · ✅ done · ❓ decision needed

---

## P1 — Architecture & correctness

### 1. ✅ Engine hardcodes the scenario path (done: c9164fe)

`engine/common/field_menu_theme.py:9-11`:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO_ROOT / "rusted_kingdoms" / "assets"
DEFAULT_BG = ASSET_ROOT / "images" / "battle_bg" / "zone4-sanctum-bg-1280x468.webp"
```

Direct violation of the engine/scenario separation rule (CLAUDE.md: "The
engine never hardcodes scenario data"). Any second scenario, or a renamed
checkout directory, silently loses the menu backdrop. This module is
imported by 23 files, so the bad dependency is everywhere.

**Action**
- Inject the scenario path (already available in `AppModule` from
  `--scenario`) into whatever owns the backdrop; kill `REPO_ROOT` /
  `ASSET_ROOT` module globals.
- Declare the menu backdrop image in the scenario (`manifest.yaml`, e.g.
  `ui.menu_backdrop: assets/images/battle_bg/zone4-sanctum-bg-1280x468.webp`)
  and raise `ValueError` naming file/property/example if absent.
- Do together with item 4 (same module).

**Done when** `grep -rn "rusted_kingdoms" engine/` returns nothing.

### 2. ✅ Enemy battle size derived from name length (done: 385372f)

`engine/battle/battle_asset_cache.py:85-86`:

```python
idx = len(enemy.name) % 3
base = [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]
```

An enemy's on-screen battle size changes when its display name is renamed
— pure accident of string length. `sprite_scale` then multiplies this
arbitrary base, so balance-neutral name edits alter visuals.

**Action**
- Add explicit `size: small|medium|large` to enemy YAML (rank files in
  `rusted_kingdoms/data/enemies/`); `boss` keeps its dedicated size.
- Missing property → `ValueError` naming file/property/example, per repo
  convention. Add a check to `tools/validate.py`.
- Migrate the current effective sizes so nothing visually changes:
  generate the list once with the old formula, write it into the YAML.

### 3. ✅ Silent fallback defaults across data loading (done — see note)

`grep -rn '\.get("[a-z_]*", ' engine --include="*.py"` → 151 hits. The
repo convention is: no hardcoded fallback values; missing required data
raises `ValueError` naming file, property, and an example. Current
hotspots: `engine/item/item_catalog.py` (7), `engine/item/item_effect_handler.py`
(4+), `engine/dialogue/dialogue_engine.py`, `engine/battle/enemy_loader.py:84`
(`sprite_scale` default 100), `engine/app_module.py:262` (`window_title`).

**Action**
- Add one helper, e.g. `engine/io/yaml_require.py`:
  `require(mapping, key, source: Path)` → value or `ValueError` with
  file/property/example.
- Sweep loaders package by package (item → dialogue → battle → world).
  For each `.get(k, default)` decide: required → `require()`; genuinely
  optional → keep `.get()` but document the default in the matching
  `docs/design/*.md`.
- Extend `tools/validate.py` so scenario authors catch missing fields
  before runtime.

**Done when** every remaining `.get(k, default)` in a loader has a
documented rationale.

**Outcome note:** the audit found most loaders already validated required
fields with ValueError+example (item_catalog, item_effect_handler,
dialogue_engine). Changes made: `engine/io/yaml_require.require()` helper;
`window_title` and `ui.menu_backdrop` now required in the manifest;
class YAML `exp_base`/`exp_factor` now required (the engine's
`_FALLBACK_EXP_BASE` scenario-data table was deleted; `calc_exp_next` is
MemberState-only); enemy `size` required; validate.py checks class exp
curves and enemy sizes. Remaining `.get(k, default)` sites are documented
optionals (drops/ai/boss flags, save-file back-compat reads, engine debug
settings) — runtime dict access outside loaders is P2 typed-models
territory, not silent scenario fallbacks.

---

## P2 — Duplication & structure

### 4. ✅ `field_menu_theme.py` is the app-wide UI kit (done: 0da5921)

417 lines in `engine/common/field_menu_theme.py` used by 23 files across
every feature (shop, inn, title, battle, dialogue, status…). It bundles:
palette constants, image/backdrop/icon caches, `render_backdrop`,
`render_modal`, `render_toast`, `render_hint`, `dim_screen`.

**Action**
- Split into `engine/common/ui/`: `theme.py` (palette), `image_cache.py`,
  `chrome.py` (backdrop/modal/toast/hint). Keep names stable enough that
  the 23 imports are a mechanical update.
- Fold in the scenario-path fix from item 1.

### 5. ✅ Lazy font-init boilerplate copy-pasted in ~26 scenes (done: e404a2d)

Every scene hand-rolls the same pattern (`engine/inn/inn_scene.py:67-79`
is representative): a `_fonts_ready` flag plus `_init_fonts()` calling
`get_fonts()` and assigning `self._font_*` attributes. 26 files do this.

**Action**
- Add a small declarative helper in `engine/common/font_provider.py`,
  e.g. `FontSet` — scenes declare `{"title": (22, True), "row": (16, False)}`
  once; first attribute access initializes lazily (fonts need pygame init,
  hence the laziness everywhere).
- Migrate scenes opportunistically (whenever a scene is touched), not as
  one big-bang PR; start with the shop family while doing item 6.

### 6. ✅ Shop family triplication (done: fb0e53a)

`engine/shop/` holds three scene+renderer pairs (item shop 328+272,
apothecary 268+305, magic-core shop 220+230) that each reimplement:
list navigation, scroll clamping, quantity picker loop, confirm state
machine, GP checks, toast feedback. Scroll-clamp logic alone appears in
10 files engine-wide (also `title/load_game_scene.py`,
`title/save_modal_scene.py`, `common/item_selection_view.py`, …).

**Action**
- Extract `engine/common/scroll_list.py` (`ScrollListState`: selection,
  clamp, page math) and `engine/common/quantity_picker.py` (qty loop,
  min/max, GP cap).
- Rebuild the three shop scenes on top; renderers keep their distinct
  layouts but consume the shared state objects.
- Then migrate the other scroll-clamp sites opportunistically.

### 7. ✅ Oversized scenes mixing flow and rendering (done — see note)

The battle package already separates scene / renderers / asset cache;
these do not:

| file | lines | smell |
|---|---|---|
| `engine/status/status_scene.py` | 689 | 10 `_render_*` methods + wizard flow + warp/target overlays |
| `engine/world/world_map_scene.py` | 578 | 27 methods, 240 `self._` references |
| `engine/item/item_scene.py` | 498 | scene + rendering (an `item_renderer.py` already exists — finish the split) |
| `engine/spell/spell_scene.py` | 426 | same pattern |
| `engine/battle/post_battle_scene.py` | 415 | reward flow + rendering |

**Action**
- One PR per file. Move `_render_*` into a sibling `*_renderer.py`
  (follow `battle_enemy_area_renderer.py` precedent); scene keeps input,
  state transitions, and logic calls.
- `status_scene` first (biggest, and already has `StatusLogic` to lean
  on); `world_map_scene` second (extract overlay/warp handling into
  `world_map_overlays`-style helpers, some exist already).

**Outcome note:** status (689→297 + StatusRenderer, c7ad039), spell
(426→231 + SpellRenderer, 0a663af), post-battle (415→158 +
PostBattleRenderer, 25910c0). `item_scene.py` and `world_map_scene.py`
turned out to already delegate all drawing (ItemRenderer /
WorldMapRenderer) — their length is input-mode flow, not mixed
rendering, so no split was needed. FontSet migration rode along:
inn, all shop renderers, and the three new renderers use it; the
remaining ~18 scenes migrate opportunistically when touched.

---

## P3 — Hygiene & follow-ups

### 8. 🟥 Test tree no longer mirrors the feature-package layout

Engine code was reorganized by feature, tests were not:
`tests/unit/state/` holds bgm/sfx/yaml/save-modal/menu tests;
`tests/unit/scenes/` mixes battle, status, shop, and world logic tests;
there are no `tests/unit/shop|inn|title|field_menu` dirs. Coverage gaps:
`item_shop_scene` (magic-core and apothecary are tested, item shop is
not), `inn_scene`, title scenes other than save-modal, shop renderers.

**Action**
- Mechanical move: relocate test files to dirs matching their engine
  subpackage (`git mv`, no content changes) so CLAUDE.md's "organized by
  subsystem" claim is true again.
- Add scene-logic tests for `item_shop_scene` buy/sell/qty paths and
  `inn_scene` rest/save flow (pure-logic level, no rendering).

### 9. 🟥 Zones 7–10 lack battle backgrounds and graded sprites to match

`zone_07_sunken_cave.yaml`, `zone_08_corrupted_forest.yaml`,
`zone_09_volcanic_region.yaml`, `zone_10_final_stronghold.yaml` have no
`background:` — battles render on the flat default floor, and their 52
enemies were graded with the `neutral` preset as a placeholder.

**Action**
- Author/commission 4 backgrounds (`zone7…zone10-bg-1280x468.webp`).
- Add `background:` to the four encounter files.
- Add presets (`cave`, `corrupted`, `volcanic`, `stronghold`) to
  `BACKGROUND_PRESETS` in `tools/make_battle_sprites.py` and regenerate:
  `python tools/make_battle_sprites.py --root rusted_kingdoms --all-encounters`.
  The tool intentionally raises on unmapped backgrounds, so forgetting
  the mapping fails loudly.

### 10. 🟥 Packaging config points outside the package

`pyproject.toml` `[tool.setuptools.package-data]` attaches
`../rusted_kingdoms/**` to the `engine` package. Scenario content is not
package data (the engine takes `--scenario <path>` at runtime), and
`../` package-data is unreliable in wheels/sdists.

**Action** — drop the `package-data` section, or if distribution of the
demo scenario is desired, restructure it as its own package. Verify with
a clean `pip install -e ".[dev]"` + game boot.

### Small stuff (batch into any nearby PR)

- `grik_the_grin_192.{png,tsx}` — the `_192` suffix suggests 192 px tiles
  but the sheet is standard 64 px / 9 cols; rename to drop the suffix
  (touch `zone_01_starting_forest.yaml` boss id + generated battle sheet).
- `engine/battle/constants.py:41-43` — `SPELLCAST_ROW_OFFSET = 0` /
  `THRUST_ROW_OFFSET = 4` comments explain the row math confusingly;
  reword ("row = Direction.DOWN(2) + offset").
- `SpriteSheet.get_portrait` head-crop ratio `10/64` is a magic number
  (`engine/world/sprite_sheet.py`); name it.
