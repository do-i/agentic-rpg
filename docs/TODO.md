# Design Gap Audit

## V1 Gap


## V2 Note (for the docs)

> In V2, the engine will accept a `--scenario` launch argument pointing to an external `story_content/` path. For V1, `story_content/` is embedded in the repo and the path is hardcoded in the engine.

Worth logging this now so the engine src doesn't get too tightly coupled to the embedded path when we write it. A single `SCENARIO_ROOT` constant in the engine will make V2 easy to wire up.