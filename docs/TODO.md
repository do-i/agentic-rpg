# Design Gap Audit

## V1 Gap

| Priority | File | NPC | Purpose | Status |
|---|---|---|---|---|
| 🔴 P1 | `intro_cutscene.yaml` | — | Game opening, sets story | ❌ Missing |
| 🔴 P1 | `elise_join.yaml` | Elise | First party join (Act 1) | ❌ Missing |
| 🔴 P1 | `reiya_join.yaml` | Reiya | Party join (Act 3) | ❌ Missing |
| 🔴 P1 | `jep_join.yaml` | Jep | Party join (Act 4) | ❌ Missing (referenced) |
| 🔴 P1 | `kael_join.yaml` | Kael | Party join (Act 2) | ❌ Missing (referenced) |
| 🟡 P2 | `elder_intro.yaml` | Elder Ardel | Story hint + reward gate | ⚠️ Stub only |
| 🟡 P2 | `millhaven_elder_hint.yaml` | Millhaven Elder | Act 2 hint | ❌ Missing (referenced) |
| 🟡 P2 | `ashenveil_oracle_hint.yaml` | Oracle | Act 3/4 hint | ❌ Missing (referenced) |
| 🟡 P2 | `guide_ardel.yaml` | Guide Ellen | Optional hint | ❌ Missing (referenced) |
| 🟢 P3 | Port master | Port Master | ✅ Done | ✅ |
| 🟢 P3 | `guide_excuses.yaml` | All guides | ✅ Done | ✅ |

## V2 Note (for the docs)

> In V2, the engine will accept a `--scenario` launch argument pointing to an external `story_content/` path. For V1, `story_content/` is embedded in the repo and the path is hardcoded in the engine.

Worth logging this now so the engine src doesn't get too tightly coupled to the embedded path when we write it. A single `SCENARIO_ROOT` constant in the engine will make V2 easy to wire up.