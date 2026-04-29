# Code Review Report

## Open items (deferred)

- **`RepositoryState.add_gp` return type drift** — `engine/party/repository_state.py:66` returns `int` but call sites still treat it as `None`. Harmless until a type-checker is wired in.
- **`engine/world/world_map_renderer.py:99-104`** — `_fade_surf` is reused across frames but refilled every frame; a future profiler pass could decide whether to keep this or simplify.
- **`engine/world/world_map_scene.py:415-426`** — `update()` runs `_engaged_enemy` deactivation before the fade / overlay checks. Works; reordering is cosmetic.
- **`engine/io/save_manager.py`** — file lacks `from __future__ import annotations`; relies on PEP 649 deferred eval pinned by `pyproject.toml >=3.14.3`. Adding the import would make the convention explicit but isn't load-bearing today.
- **pygame pin** — project pins `pygame==2.6.1` which lacks Python 3.14 wheels; CI on the declared Python version cannot install. Out of scope for the review pass.
- **Larger refactors still on the plan** — §4.3 (battle_renderer panel split), §4.4 (equip/spell wizard base), §4.5 (action_resolver split), §3.5 (`SfxManager` null-object).

## Test results

`PYTHONWARNINGS="ignore::RuntimeWarning" SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest` — **1225 passed**.

## Validation results

`python tools/validate.py --root rusted_kingdoms` — **PASS**.
