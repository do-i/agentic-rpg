# engine/battle/action_resolver.py
#
# Per-target action resolution for the battle scene. The scene's `do_resolve`
# pipes pending_action through `resolve_action` here; this module owns the
# attack/spell/item dispatch, status-effect rolls, and float emission. Turn
# ticks live in turn_advance.py; victory/defeat lives in battle_logic.py.

from __future__ import annotations

from engine.battle.battle_floats import (
    C_DEFEND, C_DMG_MAGIC, C_DMG_PHYS, C_HEAL, float_pos,
)
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_state import BattleState
from engine.battle.combatant import (
    ActiveStatus, Combatant, StatusEffect,
)
from engine.util.pseudo_random import PseudoRandom


# Mapping from spell yaml `side_effects.type` to Combatant StatusEffect.
SIDE_EFFECT_KINDS = {
    "burn":      StatusEffect.BURN,
    "freeze":    StatusEffect.FREEZE,
    "stun":      StatusEffect.STUN,
    "silence":   StatusEffect.SILENCE,
    "knockback": StatusEffect.KNOCKBACK,
    "taunt":     StatusEffect.TAUNT,
    "def_up":    StatusEffect.DEF_UP,
}


def roll_and_apply_side_effects(
    side_effects: list[dict],
    source: Combatant,
    target: Combatant,
    rng: PseudoRandom | None,
) -> list[str]:
    """Roll each side_effect's chance and apply ActiveStatus on hit.

    Burn's `damage_per_turn` is derived from caster ATK as `max(1, atk // 10)`,
    matching the scenario YAML formula `max(1, floor(enemy_atk * 0.10))`.
    Returns a list of human-readable application messages.
    """
    msgs: list[str] = []
    if not side_effects or target.is_ko:
        return msgs
    for se in side_effects:
        kind = se.get("type")
        effect = SIDE_EFFECT_KINDS.get(kind)
        if effect is None:
            continue
        chance = float(se.get("chance", 0.0))
        roll = rng.random() if rng is not None else 0.0
        if roll >= chance:
            continue
        duration = int(se["duration_turns"])
        dot = 0
        if effect is StatusEffect.BURN:
            dot = max(1, (source.atk if source else 0) // 10)
        atk_mod = float(se.get("atk_modifier", 1.0))
        def_mod = float(se.get("def_modifier", 1.0))
        target.add_status(ActiveStatus(
            effect=effect,
            duration_turns=duration,
            damage_per_turn=dot,
            atk_modifier=atk_mod,
            def_modifier=def_mod,
        ))
        msgs.append(f"{target.name} is {kind}ed!")
    return msgs


def resolve_action(state: BattleState, screen_width: int,
                   effect_handler=None, repository=None,
                   rng: PseudoRandom | None = None,
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

    # MP for spells is deducted once up front (not per target). Combatant is
    # a dataclass with field-level equality, so iterating "deduct once on the
    # first target" via target == targets[0] is unsafe — an AOE buff that
    # doesn't mutate compared fields would leave every iteration equal.
    if atype == "spell" and source and targets:
        ab = action.get("data", {})
        source.mp = max(0, source.mp - ab["mp_cost"])

    for target in targets:
        if atype == "attack":
            msg_parts.extend(_resolve_attack(
                state, source, target, screen_width, rng=rng, fx=fx,
            ))
        elif atype == "spell":
            msg_parts.extend(_resolve_spell(
                state, source, target, action, screen_width, rng=rng, fx=fx,
            ))
        elif atype == "item":
            msg_parts.extend(_resolve_item(
                state, source, target, action, screen_width,
                effect_handler=effect_handler,
            ))

    # Decrement item qty after all targets resolved.
    if atype == "item" and effect_handler and repository:
        item_id = action.get("data", {}).get("id", "")
        defn = effect_handler.get_def(item_id)
        if defn and defn.consumable:
            repository.remove_item(item_id, 1)

    state.pending_action = None
    return msg_parts[0] if msg_parts else ""


def _resolve_attack(
    state: BattleState,
    source: Combatant,
    target: Combatant,
    screen_width: int,
    *,
    rng: PseudoRandom | None,
    fx: BattleFx | None,
) -> list[str]:
    src_atk = source.effective_atk if source else 0
    dmg = max(1, src_atk - target.effective_def)
    # Basic attack is melee; back-row attacker deals halved damage.
    if source and source.row == "back":
        dmg = max(1, dmg // 2)
    # Back-row defender takes halved physical.
    if target.row == "back":
        dmg = max(1, dmg // 2)
    actual = target.apply_damage(dmg, rng)
    state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_PHYS)
    if fx:
        fx.hit(target)
    return [f"{source.name} attacked {target.name} for {actual} damage!"]


def _resolve_spell(
    state: BattleState,
    source: Combatant,
    target: Combatant,
    action: dict,
    screen_width: int,
    *,
    rng: PseudoRandom | None,
    fx: BattleFx | None,
) -> list[str]:
    ab = action.get("data", {})
    spell_type = ab.get("type", "spell")
    coeff = ab.get("spell_coeff") or ab.get("heal_coeff") or 1.0
    spell_name = ab["name"]
    msgs: list[str] = []

    if spell_type == "heal" and ab.get("revive_hp_pct"):
        if target.is_ko:
            pct = ab["revive_hp_pct"]
            target.hp = max(1, int(target.hp_max * pct))
            target.is_ko = False
            state.add_float("Revive", *float_pos(state, target, screen_width), C_HEAL)
            msgs.append(f"{source.name} casts {spell_name}! {target.name} revived!")
    elif spell_type == "heal":
        # heal_pct (% of target's hp_max) takes precedence over heal_coeff (mres-scaled).
        # See docs/design/characters.md heal-formula table.
        heal_pct = ab.get("heal_pct")
        if heal_pct is not None:
            amount = int(target.hp_max * heal_pct)
        else:
            amount = int(source.mres * coeff) if source else 10
        actual = target.apply_heal(amount)
        state.add_float(str(actual), *float_pos(state, target, screen_width), C_HEAL)
        msgs.append(f"{source.name} casts {spell_name}! {target.name} healed {actual} HP!")
    elif spell_type == "utility":
        target.clear_all_status()
        state.add_float("Cured", *float_pos(state, target, screen_width), C_HEAL)
        msgs.append(f"{source.name} casts {spell_name}! {target.name} cured!")
    elif spell_type == "buff":
        state.add_float("Buff", *float_pos(state, target, screen_width), C_HEAL)
        msgs.append(f"{source.name} casts {spell_name} on {target.name}!")
    elif spell_type == "debuff":
        state.add_float("Debuff", *float_pos(state, target, screen_width), C_DMG_MAGIC)
        msgs.append(f"{source.name} casts {spell_name} on {target.name}!")
    else:
        dmg = max(1, int(source.mres * coeff) - target.effective_def) if source else 10
        actual = target.apply_damage(dmg, rng)
        state.add_float(str(actual), *float_pos(state, target, screen_width), C_DMG_MAGIC)
        if fx:
            fx.hit(target)
        msgs.append(f"{source.name} casts {spell_name}! {actual} damage to {target.name}!")

    side_effects = ab.get("side_effects") or []
    msgs.extend(roll_and_apply_side_effects(side_effects, source, target, rng))
    return msgs


def _resolve_item(
    state: BattleState,
    source: Combatant,
    target: Combatant,
    action: dict,
    screen_width: int,
    *,
    effect_handler,
) -> list[str]:
    item_id = action.get("data", {}).get("id", "")
    item_label = item_id.replace("_", " ").title()
    defn = effect_handler.get_def(item_id) if effect_handler else None
    if defn is None:
        # Fallback for unknown items.
        actual = target.apply_heal(100)
        state.add_float(str(actual), *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used item on {target.name}! Healed {actual} HP!"]

    defn_effect = defn.effect
    effect_handler.apply_to_target(defn, target)
    if defn_effect == "revive" and target.hp > 0:
        target.is_ko = False

    if defn_effect in ("restore_hp", "restore_mp", "restore_full"):
        amount_label = str(defn.amount) if defn.amount else "Full"
        state.add_float(amount_label, *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used {item_label} on {target.name}!"]
    if defn_effect == "revive":
        state.add_float("Revive", *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used {item_label}! {target.name} revived!"]
    if defn_effect == "cure":
        state.add_float("Cured", *float_pos(state, target, screen_width), C_HEAL)
        return [f"{source.name} used {item_label} on {target.name}!"]
    state.add_float("Used", *float_pos(state, target, screen_width), C_HEAL)
    return [f"{source.name} used {item_label} on {target.name}!"]
