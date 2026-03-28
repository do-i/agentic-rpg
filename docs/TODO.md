# V1 Deliverables

## Unstub
- smooth movement: currently sprite moves into collision object - e.g., wall or tree. When such collision occurs, sprite should move left or right. make this configurable in config/settings.yaml (has bug and not working correctly)
- staus_scene: currently party stats are hardcoded. load from data/characters/aric.yaml for new game. load from saved yaml otherwise
- for debug purpose, add all members at the begining, boolean flag (config/setting.yaml) to toggle debug mode
- Player walk over NPC's head. Player sprite should go behind NPC's head.
- GP, loot, EXP should be persisted after battle and status screen should reflect these

## Feature
- Party join flow | Full party
- Shop + Apothecary | Buy/craft
- Boss encounters + story act transitions | Story progression
- Full playthrough pass | End-to-end
