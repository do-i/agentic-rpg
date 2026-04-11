# engine/battle/battle_logic.py
#
# Battle logic — action resolution, victory/defeat, enemy AI, party sync.
# Extracted from battle_scene.py to separate game logic from rendering.

from __future__ import annotations

import random

from engine.battle.combatant import Combatant
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.battle_rewards import RewardCalculator
from engine.encounter.encounter_manager import EncounterManager
from engine.battle.constants import ENEMY_AREA_H, ENEMY_LAYOUTS, ENEMY_SIZES, ROW_H
from engine.settings import Settings

# ── Layout constants needed for float positioning ─────────────
PARTY_W = Settings.SCREEN_WIDTH // 2

# ── Float colors ──────────────────────────────────────────────
C_DMG_PHYS  = (255, 180, 80)
C_DMG_MAGIC = (140, 180, 255)
C_HEAL      = (100, 220, 100)
C_DEFEND    = (180, 180, 255)


def enemy_rect_size(enemy: Combatant) -> tuple[int, int]:
    if enemy.boss:
        return ENEMY_SIZES["large"]
    idx = len(enemy.name) % 3
    return [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]


def float_pos(state: BattleState, combatant: Combatant) -> tuple[int, int]:
    """Screen position for a damage float over the given combatant."""
    if combatant.is_enemy:
        n = len(state.enemies)
        idx = state.enemies.index(combatant)
        ox, oy = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])[idx]
        cx = Settings.SCREEN_WIDTH // 2 + ox
        cy = ENEMY_AREA_H // 2 + 10 + oy
        _, h = enemy_rect_size(combatant)
        return cx - 15, cy - h // 2 - 30
    else:
        idx = state.party.index(combatant)
        return PARTY_W - 60, ENEMY_AREA_H + 8 + idx * (ROW_H + 2) + 5


def resolve_action(state: BattleState, effect_handler=None, repository=None) -> str:
    """Execute the pending action. Returns the message to display."""
    action = state.pending_action
    if not action:
        return ""
    source = action.get("source")
    targets = action.get("targets", [])
    atype = action.get("type", "attack")
    msg_parts: list[str] = []

    if atype == "defend":
        source.defending = True
        state.add_float("Defend", *float_pos(state, source), C_DEFEND)
        state.pending_action = None
        return f"{source.name} is defending!"

    for target in targets:
        if atype == "attack":
            dmg = max(1, source.atk - target.def_)
            actual = target.apply_damage(dmg)
            state.add_float(str(actual), *float_pos(state, target), C_DMG_PHYS)
            msg_parts.append(f"{source.name} attacked {target.name} for {actual} damage!")
        elif atype == "spell":
            ab = action.get("data", {})
            spell_type = ab.get("type", "spell")
            coeff = ab.get("spell_coeff") or ab.get("heal_coeff") or 1.0
            spell_name = ab.get("name", "Spell")

            if source and target == targets[0]:
                source.mp = max(0, source.mp - ab.get("mp_cost", 0))

            if spell_type == "heal" and ab.get("revive_hp_pct"):
                if target.is_ko:
                    pct = ab["revive_hp_pct"]
                    target.hp = max(1, int(target.hp_max * pct))
                    target.is_ko = False
                    state.add_float("Revive", *float_pos(state, target), C_HEAL)
                    msg_parts.append(f"{source.name} casts {spell_name}! {target.name} revived!")
            elif spell_type == "heal":
                amount = int(source.mres * coeff) if source else 10
                actual = target.apply_heal(amount)
                state.add_float(str(actual), *float_pos(state, target), C_HEAL)
                msg_parts.append(f"{source.name} casts {spell_name}! {target.name} healed {actual} HP!")
            elif spell_type == "utility":
                target.clear_all_status()
                state.add_float("Cured", *float_pos(state, target), C_HEAL)
                msg_parts.append(f"{source.name} casts {spell_name}! {target.name} cured!")
            elif spell_type == "buff":
                state.add_float("Buff", *float_pos(state, target), C_HEAL)
                msg_parts.append(f"{source.name} casts {spell_name} on {target.name}!")
            elif spell_type == "debuff":
                state.add_float("Debuff", *float_pos(state, target), C_DMG_MAGIC)
                msg_parts.append(f"{source.name} casts {spell_name} on {target.name}!")
            else:
                dmg = max(1, int(source.mres * coeff) - target.def_) if source else 10
                actual = target.apply_damage(dmg)
                state.add_float(str(actual), *float_pos(state, target), C_DMG_MAGIC)
                msg_parts.append(f"{source.name} casts {spell_name}! {actual} damage to {target.name}!")
        elif atype == "item":
            item_id = action.get("data", {}).get("id", "")
            item_label = item_id.replace("_", " ").title()
            defn = effect_handler.get_def(item_id) if effect_handler else None
            if defn:
                defn_effect = defn.effect
                effect_handler._apply_to_member(defn, target)
                # revive: clear is_ko on combatant
                if defn_effect == "revive" and target.hp > 0:
                    target.is_ko = False
                # generate float + message
                if defn_effect in ("restore_hp", "restore_mp", "restore_full"):
                    state.add_float(str(defn.amount) if defn.amount else "Full", *float_pos(state, target), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label} on {target.name}!")
                elif defn_effect == "revive":
                    state.add_float("Revive", *float_pos(state, target), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label}! {target.name} revived!")
                elif defn_effect == "cure":
                    state.add_float("Cured", *float_pos(state, target), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label} on {target.name}!")
                else:
                    state.add_float("Used", *float_pos(state, target), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label} on {target.name}!")
            else:
                # fallback for unknown items
                actual = target.apply_heal(100)
                state.add_float(str(actual), *float_pos(state, target), C_HEAL)
                msg_parts.append(f"{source.name} used item on {target.name}! Healed {actual} HP!")

    # decrement item qty after all targets resolved
    if atype == "item" and effect_handler and repository:
        item_id = action.get("data", {}).get("id", "")
        defn = effect_handler.get_def(item_id)
        if defn and defn.consumable:
            repository.remove_item(item_id, 1)

    state.pending_action = None
    return msg_parts[0] if msg_parts else ""


def resolve_enemy_turn(state: BattleState, sfx_manager=None) -> str:
    """Execute the current enemy's turn using AI data. Returns message."""
    active = state.active
    if not active or not active.is_enemy:
        return ""

    targets = state.alive_party()
    if not targets:
        return ""

    action = pick_enemy_action(active, state)
    action_type = action.get("action", "attack")
    ability_id = action.get("id", "")

    # Resolve targeting
    target_list = resolve_targeting(active, state, ability_id)
    if not target_list:
        return ""

    if action_type == "attack":
        target = target_list[0]
        alive_before = not target.is_ko
        dmg = max(1, active.atk - target.def_)
        actual = target.apply_damage(dmg)
        state.add_float(str(actual), *float_pos(state, target), C_DMG_PHYS)
        if sfx_manager:
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
        dmg = max(1, active.atk - target.def_)
        actual = target.apply_damage(dmg)
        state.add_float(str(actual), *float_pos(state, target), C_DMG_MAGIC)
        msg_parts.append(f"{target.name} took {actual} damage")
        if alive_before and target.is_ko:
            newly_ko = True
    if sfx_manager:
        sfx_manager.play("atk_impact")
        if newly_ko:
            sfx_manager.play("party_hit")

    targets_msg = ", ".join(msg_parts)
    return f"{active.name} used {ability_name}! {targets_msg}!"


# ── Enemy AI — action selection ──────────────────────────────

def pick_enemy_action(enemy: Combatant, state: BattleState) -> dict:
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
        return _weighted_pick_move(eligible)

    # default: random weighted
    return _weighted_pick_move(moves)


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


def _weighted_pick_move(moves: list[dict]) -> dict:
    """Weighted random pick from a list of move dicts."""
    if not moves:
        return {"action": "attack"}
    weights = [m.get("weight", 1) for m in moves]
    return random.choices(moves, weights=weights, k=1)[0]


# ── Enemy AI — targeting ─────────────────────────────────────

def resolve_targeting(
    enemy: Combatant, state: BattleState, ability_id: str,
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

    if mode == "all_party":
        return alive
    if mode == "self":
        return [enemy]
    if mode == "lowest_hp":
        return [min(alive, key=lambda c: c.hp)]
    if mode == "highest_hp":
        return [max(alive, key=lambda c: c.hp)]
    # random_alive (default)
    return [random.choice(alive)]


def handle_victory(
    state: BattleState,
    holder,
    boss_flag: str,
    reward_calc: RewardCalculator,
):
    """Process victory: set flags, calculate rewards, sync party. Returns rewards."""
    state.phase = BattlePhase.POST_BATTLE
    game_state = holder.get()

    if boss_flag:
        game_state.flags.add_flag(boss_flag)

    rewards = reward_calc.calculate(
        enemies=state.enemies,
        party=game_state.party,
        boss_flag=boss_flag,
    )

    sync_party_state(state, game_state.party)
    EncounterManager.add_mc_drops(game_state.repository, rewards.loot.mc_drops)
    for item in rewards.loot.item_drops:
        game_state.repository.add_item(item["id"], item.get("qty", 1))
    return rewards


def handle_defeat(state: BattleState) -> None:
    """Mark the battle as game over."""
    state.phase = BattlePhase.GAME_OVER


def sync_party_state(state: BattleState, party) -> None:
    """Write surviving HP/MP from Combatants back to MemberState."""
    combatant_map = {c.id: c for c in state.party}
    for member in party.members:
        c = combatant_map.get(member.id)
        if c is None:
            continue
        member.hp = c.hp
        member.mp = c.mp
        if c.is_ko:
            member.hp = 0


def check_result(state: BattleState) -> str:
    """Check for victory/defeat after an action resolves.
    Returns "victory", "defeat", or "continue".
    """
    if state.enemies_wiped:
        return "victory"
    if state.party_wiped:
        return "defeat"
    return "continue"


# ── Flee ─────────────────────────────────────────────────────
FLEE_BASE_CHANCE = 0.30
FLEE_ROGUE_DEX_BONUS = 0.02


def attempt_flee(state: BattleState, holder) -> tuple[bool, str]:
    """Attempt to flee from battle.

    Returns (success, message).
    Boss battles always block flee.
    Formula: 30% base + 2% per Rogue DEX in the party.
    """
    # Boss battles: cannot flee
    if any(e.boss for e in state.enemies):
        return False, "Can't escape from a boss!"

    # Calculate flee chance
    chance = FLEE_BASE_CHANCE
    party = holder.get().party
    for member in party.members:
        if member.class_name.lower() == "rogue":
            chance += FLEE_ROGUE_DEX_BONUS * member.dex

    chance = min(chance, 1.0)

    if random.random() < chance:
        return True, "Got away safely!"
    return False, "Couldn't escape!"


def advance_to_next_turn(state: BattleState) -> None:
    """Advance to the next turn and set the phase accordingly."""
    state.advance_turn()
    active = state.active
    if active:
        active.defending = False
    if active and active.is_enemy:
        state.phase = BattlePhase.ENEMY_TURN
    else:
        state.phase = BattlePhase.PLAYER_TURN
