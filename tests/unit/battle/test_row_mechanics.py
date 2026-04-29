# tests/unit/battle/test_row_mechanics.py
#
# Front/back row + attack_range — covers the four cases in
# docs/design/battle.md's summary table.

from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.battle.action_resolver import resolve_action
from engine.battle.battle_enemy_logic import resolve_enemy_turn
from engine.util.pseudo_random import PseudoRandom

SCREEN_W = 1280
_rng = PseudoRandom(seed=0)


def make_combatant(name="X", hp=100, hp_max=100, mp=50, mp_max=50,
                   atk=20, def_=5, mres=10, dex=10, is_enemy=False,
                   row="front") -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=hp, hp_max=hp_max, mp=mp, mp_max=mp_max,
        atk=atk, def_=def_, mres=mres, dex=dex,
        is_enemy=is_enemy, row=row,
    )


def make_state(party, enemies):
    return BattleState(party=party, enemies=enemies)


# ── Outgoing physical (basic attack) ─────────────────────────────

class TestOutgoingMelee:
    def test_front_row_melee_full_damage(self):
        # Front melee → full damage. atk 20 - def 5 = 15.
        attacker = make_combatant("Hero", atk=20, row="front")
        target = make_combatant("Goblin", hp=50, hp_max=50, def_=5, is_enemy=True)
        state = make_state([attacker], [target])
        state.pending_action = {"type": "attack", "source": attacker, "targets": [target]}

        resolve_action(state, SCREEN_W)
        assert target.hp == 35  # 50 - 15

    def test_back_row_melee_halved(self):
        # Back row dealing melee → half damage. floor(15 * 0.5) = 7.
        attacker = make_combatant("Rogue", atk=20, row="back")
        target = make_combatant("Goblin", hp=50, hp_max=50, def_=5, is_enemy=True)
        state = make_state([attacker], [target])
        state.pending_action = {"type": "attack", "source": attacker, "targets": [target]}

        resolve_action(state, SCREEN_W)
        assert target.hp == 43  # 50 - 7

    def test_back_row_melee_floors_to_one(self):
        # Halving must never reduce damage below 1.
        attacker = make_combatant("Rogue", atk=6, row="back")
        target = make_combatant("Goblin", hp=10, hp_max=10, def_=5, is_enemy=True)
        state = make_state([attacker], [target])
        state.pending_action = {"type": "attack", "source": attacker, "targets": [target]}

        resolve_action(state, SCREEN_W)
        # base = max(1, 6-5) = 1; back row halves → max(1, 1//2) = 1.
        assert target.hp == 9


# ── Incoming physical to back-row party member ───────────────────

class TestIncomingPhysical:
    def test_back_row_takes_half_physical(self):
        hero = make_combatant("Hero", hp=100, hp_max=100, def_=5, row="back")
        goblin = make_combatant("Goblin", atk=15, is_enemy=True)
        state = make_state([hero], [goblin])
        state.build_turn_order()
        state.active_index = state.turn_order.index(goblin)

        resolve_enemy_turn(state, SCREEN_W, rng=_rng)
        # base = 15 - 5 = 10; back row halves → 5.
        assert hero.hp == 95

    def test_front_row_takes_full_physical(self):
        hero = make_combatant("Hero", hp=100, hp_max=100, def_=5, row="front")
        goblin = make_combatant("Goblin", atk=15, is_enemy=True)
        state = make_state([hero], [goblin])
        state.build_turn_order()
        state.active_index = state.turn_order.index(goblin)

        resolve_enemy_turn(state, SCREEN_W, rng=_rng)
        assert hero.hp == 90  # 100 - (15-5)


# ── Spell ignores row ────────────────────────────────────────────

class TestSpellIgnoresRow:
    def test_back_row_caster_full_spell_damage(self):
        # spell uses int * spell_coeff - def — row never enters the formula.
        sorc = make_combatant("Sorc", mp=30, mres=15, row="back")
        goblin = make_combatant("Goblin", hp=50, hp_max=50, def_=3, is_enemy=True)
        state = make_state([sorc], [goblin])
        spell = {"name": "Fire", "type": "spell", "spell_coeff": 2.0, "mp_cost": 8}
        state.pending_action = {
            "type": "spell", "data": spell, "source": sorc, "targets": [goblin],
        }

        resolve_action(state, SCREEN_W)
        # dmg = max(1, int(15 * 2.0) - 3) = 27. No row penalty.
        assert goblin.hp == 23

    def test_back_row_heal_full_amount(self):
        cleric = make_combatant("Cleric", mp=30, mres=20, row="back")
        ally = make_combatant("Ally", hp=50, hp_max=100, row="back")
        state = make_state([cleric, ally], [make_combatant("G", is_enemy=True)])
        spell = {"name": "Heal", "type": "heal", "heal_coeff": 2.0, "mp_cost": 10,
                 "target": "single_ally"}
        state.pending_action = {
            "type": "spell", "data": spell, "source": cleric, "targets": [ally],
        }

        resolve_action(state, SCREEN_W)
        assert ally.hp == 90  # 50 + 40 — full
