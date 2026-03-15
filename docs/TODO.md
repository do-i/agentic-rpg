# Design Gap Audit

## V1 Suggested Engine Build Order

| Phase | Deliverable | Playable? |
|---|---|---|
| 1 | Boot → load manifest → world map render + player movement | Walk around |
| 2 | Town entry → NPC interaction → dialogue engine | Talk to NPCs |
| 3 | Flag system + save/load | Persist state |
| 4 | Random encounter → battle system → exp/loot | Fight enemies |
| 5 | Party join flow | Full party |
| 6 | Shop + Apothecary | Buy/craft |
| 7 | Boss encounters + story act transitions | Story progression |
| 8 | Full playthrough pass | End-to-end |


## V2 Note (for the docs)

> In V2, the engine will accept a `--scenario` launch argument pointing to an external `story_content/` path. For V1, `story_content/` is embedded in the repo and the path is hardcoded in the engine.

Worth logging this now so the engine src doesn't get too tightly coupled to the embedded path when we write it. A single `SCENARIO_ROOT` constant in the engine will make V2 easy to wire up.