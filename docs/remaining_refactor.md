# TODO

- Create more TMX (map files)
- attribute each tile (for AI agent)
- change encounter system enemy is visible
- find a auto pygame test method
- enemy does not chase player

## Battle Hit Effects — Follow-ups

Shipped: `BattleFx` service (`engine/battle/battle_fx.py`) wired through
`battle_logic`, `battle_enemy_logic`, and `BattleRenderer` — white flash +
hurt shake on every damaging hit. Floating damage numbers were already
present on `BattleState.damage_floats`.

Possible next steps:

- Element / action-type decals (slash, fire puff, ice shards, thunder) over the target, keyed off the same action switch `SfxManager.play_battle_action` uses.
- Red flash for physical vs white for magic, or crit-only brighter flash + 2× shake.
- Damage number upgrades: "MISS" text, crit flair, bigger font for crits.
- Death fade/dissolve on 0 HP instead of the instant alpha=80 on KO.
- Status-inflict ping overlay when a debuff applies (e.g. green wisp for poison).
