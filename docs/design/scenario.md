# 17. Scenario Manifest

## Schema

See story_content


## Key Design Points

| Decision | Rule |
|---|---|
| One protagonist per scenario | Fixed — no multi-hero support in V1 |
| Protagonist name | Default from manifest, player can rename at New Game |
| Party join order | Driven by `join_condition` flag — story-gated |
| Last member join | Must be enforced at 10–15% story remaining (per `party.md`) |
| `refs` block | Tells engine where to find each subsystem's files |
| Flag IDs | All flags used across all files must be unique — manifest is source of truth |