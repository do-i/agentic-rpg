---
name: validate-scenario
description: This skill should be used when the user wants to "validate the scenario", "check the data", "run validation", "check for broken links", "audit flags", "check for errors", or wants to verify the scenario is consistent before committing or after adding new content.
version: 0.1.0
---

# Validate Scenario

Run both checks in sequence and interpret the results.

## Commands

```sh
# From the repo root:
python tools/validate.py --root rusted_kingdoms
python -m pytest
```

Or combined in one shot:

```sh
python tools/validate.py --root rusted_kingdoms && python -m pytest
```

## Interpreting validate.py Output

The validator runs three passes. Fix in this order — earlier passes can mask later issues.

### BROKEN LINKS (errors — fix immediately)
- A file referenced by ID or path doesn't exist.
- Common causes: typo in an `id`, wrong path in `dialogue:` field, item referenced in a shop or recipe but not defined in `data/items/`.
- **Fix**: correct the ID/path or add the missing file.

### UNREACHABLE FILES (warnings — review, not always a bug)
- A YAML file exists but nothing references it.
- May be intentional (content in progress, disabled content).
- **Fix if unintentional**: wire it to a map/NPC/recipe, or delete it.

### FLAG AUDIT

**Consumed but never defined** (errors — fix immediately):
- A `requires:` or `excludes:` condition checks a flag that is never set anywhere.
- The condition will never be true (or always be false), breaking progression.
- **Fix**: add a `set_flag:` in the appropriate dialogue `on_complete`, or correct the flag name typo.

**Defined but never consumed** (warnings — review):
- A `set_flag:` fires but nothing ever checks that flag.
- May be intentional (future use, engine-managed flags).
- **Fix if unintentional**: add a condition that uses it, or remove the `set_flag`.

## Interpreting pytest Output

Pytest runs with `-v -x` (verbose, stop on first failure).

- A failing test pinpoints a code regression — fix before committing.
- `RuntimeWarning` spam can be suppressed: `PYTHONWARNINGS="ignore::RuntimeWarning" python -m pytest`

## When to Run

- After adding any new content (enemy, item, NPC, dialogue, encounter zone).
- Before committing — broken links and undefined flags are commit-blocking errors.
- After renaming or deleting any ID — both passes catch dangling references.
