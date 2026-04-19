# TODO

- Create more TMX (map files)
- attribute each tile (for AI agent)
- change encounter system enemy is visible
- find a auto pygame test method

## Battle Hit Effects — Plan

### Ideas (cheap → flashy)

1. **White flash** — recolor the sprite to pure white for ~80ms on hit. Iconic FFVI / Chrono Trigger feel. One-liner with a surface fill + `BLEND_RGBA_MULT`. *Best ROI.*
2. **Hurt shake** — offset sprite blit by `(±dx, 0)` over ~180ms (3–4 wiggles). Combines beautifully with #1.
3. **Red tint** — modulate toward red instead of white for elemental / physical distinction.
4. **Floating damage number** — `-42` popup that rises and fades over ~500ms above the sprite. Huge readability boost.
5. **Impact decal** — a slash / spark / burst sprite drawn over the target for ~150ms (element-specific: slash, fire puff, ice shards, thunder crack). Reuses the SFX keys already wired in `SfxManager.play_battle_action`.
6. **Screen shake** — whole camera offset on big hits / crits. Use sparingly.
7. **Squash-stretch** — brief non-uniform scale on sprite (e.g. 1.1×0.9 → 1.0×1.0).
8. **Miss / crit flair** — "MISS" text; crit gets a brighter flash + shake amplitude 2×.
9. **Death fade / dissolve** — on 0 HP, alpha-fade out (or pixelate dissolve) instead of vanishing instantly.
10. **Status-inflict ping** — distinct one-shot overlay when a debuff applies (e.g. green wisp for poison).

### Minimal plan

1. **Add `BattleFx` service** (`engine/battle/battle_fx.py`) holding a list of active effects, each with a timer + target id. Methods:
   - `flash(target_id)`
   - `shake(target_id)`
   - `floating_text(target_id, text, color)`
   - `decal(target_id, key)`
2. **Wire it in `battle_logic.py`** where `apply_damage` is called — emit flash + shake + damage number; optional decal based on action type (reuse the switch in `SfxManager.play_battle_action`).
3. **Drive it from `BattleRenderer.render`** — read active effects, apply sprite transforms (shake offset, color mult, scale), draw damage-number overlay last. Effects tick their timers on render using delta (pass `dt` into render if not already).
4. **Start minimal:** #1 + #2 + #4 together gets you 80% of the feel; add #5 (element decal) once the framework exists. Register in `AppModule`.

### Recommendation

Build the `BattleFx` service first and ship **white flash + hurt shake + floating damage number** in one go — three effects but they reuse the same timer plumbing and together they make hits *feel* landed. Element decals are a great follow-up once the pipeline works.
