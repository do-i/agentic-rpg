# 22. NPC

## NPC animation modes (configured per-NPC in map YAML)
- still — static idle frame (default, unchanged behavior)
- step — cycles walk frames in place (stationary stepping)
- wander — moves randomly within range tiles of origin, pauses between moves

## Config options in YAML animation: block
- mode: still | step | wander
- speed: frame speed multiplier (default 1.0, lower = slower)
- range: wander radius in tiles (default 2, only for wander mode)

## Behavior
- NPCs freeze animation and face the player when nearby
- Wandering NPCs pause 1-3.5s between moves
- Walk frames cycle columns 1-8, idle is column 0
- world_map_scene now calls npc.update(delta) each frame