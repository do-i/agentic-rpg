# Code Review Plan

Date: 2026-04-27
Scope: `engine/` and `tests/` (199 source files, 14,742 LOC engine; 64 test files, 9,224 LOC tests, 892 tests).
Method: Read-only review focused on five axes: bugs, performance, duplication, breaking up oversized modules, and test gaps.

Severity tags:
- **P1** — broken / data loss / incorrect game behavior. Fix before next release.
- **P2** — wrong-but-benign or fragile. Schedule.
- **P3** — code smell / style / minor inefficiency.

All P1/P2 items called out in the original review have landed. The notes below track the remaining P3 items deferred as out-of-scope.

---

## Out of scope (noted, not pursued)

- **§2.9 [P3] Autosave on every portal transition** (`engine/world/world_map_logic.py:145`). `game_state_manager.save(state, slot_index=0)` writes a full YAML save on every portal traversal. Acceptable for an SSD; revisit if many small maps cause noticeable churn (debounce or only autosave on entering "checkpoint" maps).
- **§3.6 [P3] `_clamp_scroll` per shop scene** (`item_shop_scene.py:156-159`, `apothecary_scene.py:198-201`). Both bodies are a 1-line wrapper around `ItemSelectionView.clamp_scroll` that differ only in the source list (`_available()` vs `_visible_recipes()`). Extracting would not shorten either site; left inlined.
- **§3.7 [P3] `.get(k, default)` audit** — touches dozens of files (`map_state.py`, `dialogue_engine.py`, `item_catalog.py`, `item_effect_handler.py`, …) and is a project-wide policy enforcement task; recommend a separate ticket.
- **§4.7 [P3] ~300-line modules** — `engine/status/status_renderer.py` (329), `engine/item/item_renderer.py` (318), `engine/encounter/enemy_sprite.py` (307), `engine/shop/apothecary_renderer.py` (305), `engine/world/npc.py` (303). All under threshold and reasonably cohesive; revisit if any cross 400.
- **§5.7 [P3] Test directory consolidation** — `tests/unit/core/` and `tests/unit/world/` split is already noted in CLAUDE.md ("legacy path"); plan a rename pass once unrelated work settles.
