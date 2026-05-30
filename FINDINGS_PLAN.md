# Findings Plan

1. [x] Fix boss-only map spawning.
   - Problem: `engine/world/world_map_init.py` only builds an `EnemySpawner` when `spawn_tile` entries exist. A map with only a `boss_enemy` object layer skips boss spawning entirely.
   - Verify: add/use a map with a `boss_enemy` layer and no `spawn_tile` layer; entering the map should show the boss sprite and trigger its battle on collision.

2. [x] Verify save checksums on load.
   - Problem: `GameStateManager.list_slots()` detects checksum mismatches, but `GameStateManager.load()` ignores the checksum and loads tampered files.
   - Verify: corrupt a saved YAML payload after save; the load flow should reject it or surface an unreadable slot instead of restoring the state.

3. [ ] Only mark a world enemy engaged when battle launch succeeds.
   - Problem: `WorldMapScene._launch_battle_from_enemy()` stores `_engaged_enemy` before knowing whether `launch_battle_from_enemy()` built and switched to a battle scene.
   - Verify: make an encounter formation resolve to no valid enemies; colliding with that visible enemy should not silently deactivate it unless battle starts.

4. [ ] Make playback speed honor fractional values.
   - Problem: `Game.run()` rounds playback speed to whole update steps, so documented values like `0.5` behave like `1.0`.
   - Verify: play back the same recording at `--playback-speed 0.5`, `1.0`, and `2.0`; elapsed playback should scale accordingly.

5. [ ] Pre-scale world sprite frames.
   - Opportunity: player, NPC, and world enemy render paths call `pygame.transform.scale()` every frame.
   - Verify: profile frame time on a populated map before and after caching scaled frames.

6. [ ] Cache loaded enemy definitions or combatant templates.
   - Opportunity: `EnemyLoader.load()` reparses a multi-document rank YAML file for every enemy load.
   - Verify: profile repeated battle launches or encounter resolution; enemy loads should avoid repeated YAML parsing.

7. [ ] Reduce per-enemy collision-list allocation.
   - Opportunity: `EnemySpawner.update()` creates sliced `other_rects` lists for every active enemy, which remains O(N^2) allocation as spawn counts grow.
   - Verify: profile maps with high enemy counts; update allocation and frame time should drop.

8. [ ] Cache save-modal dim overlay surface.
   - Opportunity: `SaveModalScene.render()` allocates a full-screen alpha surface every frame.
   - Verify: open the save modal and profile allocation/frame time before and after caching the overlay.
