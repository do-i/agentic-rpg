# tests/unit/core/battle/test_combatant.py

from __future__ import annotations

import pytest
from engine.battle.combatant import ActiveStatus, Combatant, StatusEffect
from engine.battle.battle_state import BattleState, BattlePhase
from engine.util.pseudo_random import PseudoRandom


def poison(duration: int = 3) -> ActiveStatus:
    return ActiveStatus(effect=StatusEffect.POISON, duration_turns=duration)


def sleep(duration: int = 3) -> ActiveStatus:
    return ActiveStatus(effect=StatusEffect.SLEEP, duration_turns=duration)

_rng = PseudoRandom(seed=0)


def make_combatant(name="Aric", hp=100, mp=40, atk=20, def_=10,
                   mres=8, dex=14, is_enemy=False) -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=hp, hp_max=hp, mp=mp, mp_max=mp,
        atk=atk, def_=def_, mres=mres, dex=dex,
        is_enemy=is_enemy,
    )


def make_battle(party_n=2, enemy_n=2) -> BattleState:
    party   = [make_combatant(f"Hero{i}",  dex=14-i) for i in range(party_n)]
    enemies = [make_combatant(f"Enemy{i}", dex=10+i, is_enemy=True) for i in range(enemy_n)]
    return BattleState(party=party, enemies=enemies)


# ── Combatant ─────────────────────────────────────────────────

class TestCombatant:
    def test_apply_damage_reduces_hp(self):
        c = make_combatant(hp=100)
        c.apply_damage(30, _rng)
        assert c.hp == 70

    def test_apply_damage_clamps_to_zero(self):
        c = make_combatant(hp=20)
        c.apply_damage(50, _rng)
        assert c.hp == 0

    def test_apply_damage_sets_ko(self):
        c = make_combatant(hp=10)
        c.apply_damage(10, _rng)
        assert c.is_ko

    def test_apply_damage_returns_actual(self):
        c = make_combatant(hp=20)
        actual = c.apply_damage(50, _rng)
        assert actual == 20

    def test_apply_heal_restores_hp(self):
        c = make_combatant(hp=50)
        c.hp = 30
        c.apply_heal(10)
        assert c.hp == 40

    def test_apply_heal_clamps_to_max(self):
        c = make_combatant(hp=100)
        c.hp = 90
        c.apply_heal(50)
        assert c.hp == 100

    def test_apply_heal_no_effect_on_ko(self):
        c = make_combatant(hp=100)
        c.hp = 0
        c.is_ko = True
        result = c.apply_heal(50)
        assert result == 0
        assert c.hp == 0

    def test_hp_pct(self):
        c = make_combatant(hp=100)
        c.hp = 25
        assert c.hp_pct == pytest.approx(0.25)

    def test_status_add_remove(self):
        c = make_combatant()
        c.add_status(poison())
        assert c.has_status(StatusEffect.POISON)
        c.remove_status(StatusEffect.POISON)
        assert not c.has_status(StatusEffect.POISON)

    def test_status_no_duplicate(self):
        c = make_combatant()
        c.add_status(sleep(duration=2))
        c.add_status(sleep(duration=4))
        assert len(c.status_effects) == 1
        assert c.status_effects[0].duration_turns == 4  # refresh, not stack

    def test_clear_all_status(self):
        c = make_combatant()
        c.add_status(poison())
        c.add_status(sleep())
        c.clear_all_status()
        assert c.status_effects == []


# ── BattleState ───────────────────────────────────────────────

class TestBattleState:
    def test_build_turn_order_dex_descending(self):
        b = make_battle()
        b.build_turn_order()
        dexes = [c.dex for c in b.turn_order]
        assert dexes == sorted(dexes, reverse=True)

    def test_active_returns_first_in_order(self):
        b = make_battle()
        b.build_turn_order()
        assert b.active is b.turn_order[0]

    def test_advance_turn_moves_index(self):
        b = make_battle()
        b.build_turn_order()
        first = b.active
        b.advance_turn()
        assert b.active is not first

    def test_party_wiped_true(self):
        b = make_battle(party_n=2)
        for m in b.party:
            m.hp = 0
            m.is_ko = True
        assert b.party_wiped

    def test_party_wiped_false(self):
        b = make_battle(party_n=2)
        assert not b.party_wiped

    def test_enemies_wiped(self):
        b = make_battle(enemy_n=2)
        for e in b.enemies:
            e.hp = 0
            e.is_ko = True
        assert b.enemies_wiped

    def test_alive_enemies_excludes_ko(self):
        b = make_battle(enemy_n=2)
        b.enemies[0].hp = 0
        b.enemies[0].is_ko = True
        assert len(b.alive_enemies()) == 1

    def test_damage_float_added(self):
        b = make_battle()
        b.add_float("42", 100, 200, (255, 0, 0))
        assert len(b.damage_floats) == 1

    def test_damage_floats_expire(self):
        b = make_battle()
        b.add_float("10", 0, 0, (255, 255, 255))
        b.update_floats(2.0)   # large delta → alpha hits 0
        assert len(b.damage_floats) == 0
