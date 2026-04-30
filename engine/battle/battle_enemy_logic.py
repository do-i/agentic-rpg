# engine/battle/battle_enemy_logic.py
#
# Enemy AI — action selection, targeting, and turn resolution.
# Extracted from battle_logic.py to separate enemy AI from player action logic.

from __future__ import annotations

from engine.battle.combatant import Combatant
from engine.battle.battle_state import BattleState
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_logic import float_pos, enemy_rect_size, C_DMG_PHYS, C_DMG_MAGIC
from engine.util.pseudo_random import PseudoRandom


def resolve_enemy_turn(state: BattleState, screen_width: int,
                       sfx_manager,
                       rng: PseudoRandom | None = None,
                       fx: BattleFx | None = None) -> str:
    """Execute the current enemy's turn using AI data. Returns message."""
    active = state.active
    if not active or not active.is_enemy:
        return ""

    targets = state.alive_party()
    if not targets:
        return ""

    action = pick_enemy_action(active, state, rng)
    action_type = action.get("action", "attack")
    ability_id = action.get("id", "")

    # Resolve targeting
    target_list = resolve_targeting(active, state, ability_id, rng)
    if not target_list:
        return ""

    if action_type == "attack":
        target = target_list[0]
        alive_before = not target.is_ko
        dmg = max(1, active.atk - target.effective_def)
        # Back-row party member halves incoming physical damage.
        if target.row == "back":
            dmg = max(1, dmg // 2)
        actual = target.apply_damage(dmg, rng)
        state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_PHYS)
        if fx:
            fx.hit(target)
        sfx_manager.play("atk_impact")
        if alive_before and target.is_ko:
            sfx_manager.play("party_hit")
        return f"{active.name} attacked {target.name} for {actual} damage!"

    # ability — display ability name, deal ATK-based damage to targets
    ability_name = ability_id.replace("_", " ").title()
    msg_parts: list[str] = []
    newly_ko = False
    for target in target_list:
        alive_before = not target.is_ko
        dmg = max(1, active.atk - target.effective_def)
        actual = target.apply_damage(dmg, rng)
        state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_MAGIC)
        if fx:
            fx.hit(target)
        msg_parts.append(f"{target.name} took {actual} damage")
        if alive_before and target.is_ko:
            newly_ko = True
    sfx_manager.play("atk_impact")
    if newly_ko:
        sfx_manager.play("party_hit")

    targets_msg = ", ".join(msg_parts)
    return f"{active.name} used {ability_name}! {targets_msg}!"


# ── Enemy AI — action selection ──────────────────────────────

def pick_enemy_action(enemy: Combatant, state: BattleState, rng: PseudoRandom | None = None) -> dict:
    """Pick an action from the enemy's AI move list.

    Supports patterns:
      - random: weighted pick from all moves
      - conditional: filter moves by hp_pct_below / turn_mod, then weighted pick
    Falls back to basic attack if no AI data or no eligible moves.
    """
    ai_block = enemy.ai_data.get("ai", {})
    moves = ai_block.get("moves", [])
    if not moves:
        return {"action": "attack"}

    pattern = ai_block.get("pattern", "random")

    if pattern == "conditional":
        eligible = [m for m in moves if _check_condition(m, enemy, state)]
        if not eligible:
            return {"action": "attack"}
        return _weighted_pick_move(eligible, rng)

    # default: random weighted
    return _weighted_pick_move(moves, rng)


def _check_condition(move: dict, enemy: Combatant, state: BattleState) -> bool:
    """Check whether a conditional move is eligible."""
    cond = move.get("condition")
    if not cond:
        return True

    hp_threshold = cond.get("hp_pct_below")
    if hp_threshold is not None and enemy.hp_pct >= hp_threshold:
        return False

    turn_mod = cond.get("turn_mod")
    if turn_mod is not None:
        every = turn_mod.get("every", 1)
        if every > 0 and state.turn_count % every != 0:
            return False

    return True


def _weighted_pick_move(moves: list[dict], rng: PseudoRandom | None = None) -> dict:
    """Weighted random pick from a list of move dicts."""
    if not moves:
        return {"action": "attack"}
    weights = [m.get("weight", 1) for m in moves]
    return rng.choices(moves, weights=weights, k=1)[0]


# ── Enemy AI — targeting ─────────────────────────────────────

def resolve_targeting(
    enemy: Combatant, state: BattleState, ability_id: str,
    rng: PseudoRandom | None = None,
) -> list[Combatant]:
    """Pick target(s) for the enemy's action based on targeting data."""
    targeting = enemy.ai_data.get("targeting", {})
    default_mode = targeting.get("default", "random_alive")

    # Check for ability-specific override
    mode = default_mode
    for override in targeting.get("overrides", []):
        if override.get("ability") == ability_id:
            mode = override.get("target", default_mode)
            break

    alive = state.alive_party()
    if not alive:
        return []

    # all_party AOE bypasses taunt; self targets the caster.
    if mode == "all_party":
        return alive
    if mode == "self":
        return [enemy]

    # Single-target modes: any taunting party member forces the pick.
    taunters = [c for c in alive if c.is_taunting]
    pool = taunters if taunters else alive

    if mode == "lowest_hp":
        return [min(pool, key=lambda c: c.hp)]
    if mode == "highest_hp":
        return [max(pool, key=lambda c: c.hp)]
    # random_alive (default)
    return [rng.choice(pool)]
