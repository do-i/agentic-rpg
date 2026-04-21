# engine/battle/battle_logic.py
#
# Battle logic — action resolution, victory/defeat, party sync, flee.
# Enemy AI lives in battle_enemy_logic.py.

from __future__ import annotations

from engine.battle.combatant import Combatant
from engine.util.pseudo_random import PseudoRandom
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.battle_rewards import RewardCalculator
from engine.battle.battle_fx import BattleFx
from engine.encounter.encounter_manager import EncounterManager
from engine.battle.constants import ENEMY_AREA_H, ENEMY_LAYOUTS, ENEMY_SIZES, ROW_H
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


def float_pos(state: BattleState, combatant: Combatant,
              screen_width: int = 1280) -> tuple[int, int]:
    """Screen position for a damage float over the given combatant."""
    if combatant.is_enemy:
        n = len(state.enemies)
        idx = state.enemies.index(combatant)
        ox, oy = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])[idx]
        cx = screen_width // 2 + ox
        cy = ENEMY_AREA_H // 2 + 10 + oy
        _, h = enemy_rect_size(combatant)
        return cx - 15, cy - h // 2 - 30
    else:
        idx = state.party.index(combatant)
        party_w = screen_width // 2
        return party_w - 60, ENEMY_AREA_H + 8 + idx * (ROW_H + 2) + 5


def resolve_action(state: BattleState, effect_handler=None, repository=None,
                   screen_width: int = 1280, rng: PseudoRandom | None = None,
                   fx: BattleFx | None = None) -> str:
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
        state.add_float("Defend", *float_pos(state, source, screen_width), C_DEFEND)
        state.pending_action = None
        return f"{source.name} is defending!"

    for target in targets:
        if atype == "attack":
            dmg = max(1, source.atk - target.def_)
            actual = target.apply_damage(dmg, rng)
            state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_PHYS)
            if fx:
                fx.hit(target)
            msg_parts.append(f"{source.name} attacked {target.name} for {actual} damage!")
        elif atype == "spell":
            ab = action.get("data", {})
            spell_type = ab.get("type", "spell")
            coeff = ab.get("spell_coeff") or ab.get("heal_coeff") or 1.0
            spell_name = ab["name"]

            if source and target == targets[0]:
                source.mp = max(0, source.mp - ab["mp_cost"])

            if spell_type == "heal" and ab.get("revive_hp_pct"):
                if target.is_ko:
                    pct = ab["revive_hp_pct"]
                    target.hp = max(1, int(target.hp_max * pct))
                    target.is_ko = False
                    state.add_float("Revive", *float_pos(state, target, screen_width), C_HEAL)
                    msg_parts.append(f"{source.name} casts {spell_name}! {target.name} revived!")
            elif spell_type == "heal":
                amount = int(source.mres * coeff) if source else 10
                actual = target.apply_heal(amount)
                state.add_float(str(actual), *float_pos(state, target, screen_width), C_HEAL)
                msg_parts.append(f"{source.name} casts {spell_name}! {target.name} healed {actual} HP!")
            elif spell_type == "utility":
                target.clear_all_status()
                state.add_float("Cured", *float_pos(state, target, screen_width), C_HEAL)
                msg_parts.append(f"{source.name} casts {spell_name}! {target.name} cured!")
            elif spell_type == "buff":
                state.add_float("Buff", *float_pos(state, target, screen_width), C_HEAL)
                msg_parts.append(f"{source.name} casts {spell_name} on {target.name}!")
            elif spell_type == "debuff":
                state.add_float("Debuff", *float_pos(state, target, screen_width), C_DMG_MAGIC)
                msg_parts.append(f"{source.name} casts {spell_name} on {target.name}!")
            else:
                dmg = max(1, int(source.mres * coeff) - target.def_) if source else 10
                actual = target.apply_damage(dmg, rng)
                state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_MAGIC)
                if fx:
                    fx.hit(target)
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
                    state.add_float(str(defn.amount) if defn.amount else "Full", *float_pos(state, target, screen_width), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label} on {target.name}!")
                elif defn_effect == "revive":
                    state.add_float("Revive", *float_pos(state, target, screen_width), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label}! {target.name} revived!")
                elif defn_effect == "cure":
                    state.add_float("Cured", *float_pos(state, target, screen_width), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label} on {target.name}!")
                else:
                    state.add_float("Used", *float_pos(state, target, screen_width), C_HEAL)
                    msg_parts.append(f"{source.name} used {item_label} on {target.name}!")
            else:
                # fallback for unknown items
                actual = target.apply_heal(100)
                state.add_float(str(actual), *float_pos(state, target, screen_width), C_HEAL)
                msg_parts.append(f"{source.name} used item on {target.name}! Healed {actual} HP!")

    # decrement item qty after all targets resolved
    if atype == "item" and effect_handler and repository:
        item_id = action.get("data", {}).get("id", "")
        defn = effect_handler.get_def(item_id)
        if defn and defn.consumable:
            repository.remove_item(item_id, 1)

    state.pending_action = None
    return msg_parts[0] if msg_parts else ""


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
# Fallback defaults — authoritative values live in the scenario balance YAML
# and flow in through the `balance` parameter.
FLEE_BASE_CHANCE = 0.30
FLEE_ROGUE_DEX_BONUS = 0.02


def attempt_flee(state: BattleState, holder, rng: PseudoRandom,
                 balance=None) -> tuple[bool, str]:
    """Attempt to flee from battle.

    Returns (success, message).
    Boss battles always block flee.
    Formula: base_chance + dex_bonus per Rogue DEX in the party.
    Values sourced from balance.yaml when `balance` is supplied.
    """
    # Boss battles: cannot flee
    if any(e.boss for e in state.enemies):
        return False, "Can't escape from a boss!"

    base_chance    = balance.flee_base_chance     if balance else FLEE_BASE_CHANCE
    rogue_dex_bonus = balance.flee_rogue_dex_bonus if balance else FLEE_ROGUE_DEX_BONUS

    # Calculate flee chance
    chance = base_chance
    party = holder.get().party
    for member in party.members:
        if member.class_name.lower() == "rogue":
            chance += rogue_dex_bonus * member.dex

    chance = min(chance, 1.0)

    if rng.random() < chance:
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
