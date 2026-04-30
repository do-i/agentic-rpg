# tests/unit/core/battle/test_battle_state.py

from __future__ import annotations

from engine.battle.battle_state import BattleState, BattlePhase, DamageFloat
from engine.battle.combatant import Combatant


def make_combatant(name="X", dex=10, is_enemy=False, hp=100, is_ko=False) -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=hp, hp_max=100, mp=10, mp_max=10,
        atk=10, def_=5, mres=5, dex=dex,
        is_enemy=is_enemy, boss=False,
        is_ko=is_ko,
        abilities=[], ai_data={},
    )


# ── build_turn_order ──────────────────────────────────────────

class TestBuildTurnOrder:
    def test_orders_by_dex_descending(self):
        a = make_combatant("A", dex=8)
        b = make_combatant("B", dex=12)
        c = make_combatant("C", dex=5)
        state = BattleState(party=[a, b, c], enemies=[])
        state.build_turn_order()
        assert [m.name for m in state.turn_order] == ["B", "A", "C"]

    def test_party_wins_dex_ties_over_enemies(self):
        # Tie-break: party (is_enemy=False) before enemies (is_enemy=True).
        # Sort key (dex, not is_enemy) reverse=True → not False=True > not True=False.
        hero = make_combatant("Hero", dex=10, is_enemy=False)
        slime = make_combatant("Slime", dex=10, is_enemy=True)
        state = BattleState(party=[hero], enemies=[slime])
        state.build_turn_order()
        assert state.turn_order[0] is hero

    def test_excludes_dead_combatants(self):
        alive = make_combatant("A", hp=10)
        dead = make_combatant("B", hp=0, is_ko=True)
        state = BattleState(party=[alive, dead], enemies=[])
        state.build_turn_order()
        assert dead not in state.turn_order

    def test_resets_active_index_to_zero(self):
        state = BattleState(party=[make_combatant("A")], enemies=[])
        state.active_index = 99
        state.build_turn_order()
        assert state.active_index == 0


# ── advance_turn ──────────────────────────────────────────────

class TestAdvanceTurn:
    def test_moves_to_next_alive(self):
        a = make_combatant("A", dex=10)
        b = make_combatant("B", dex=8)
        c = make_combatant("C", dex=6)
        state = BattleState(party=[a, b, c], enemies=[])
        state.build_turn_order()
        assert state.active is a
        state.advance_turn()
        assert state.active is b

    def test_skips_dead_combatant(self):
        a = make_combatant("A", dex=10)
        b = make_combatant("B", dex=8)
        c = make_combatant("C", dex=6)
        state = BattleState(party=[a, b, c], enemies=[])
        state.build_turn_order()
        b.is_ko = True
        b.hp = 0
        state.advance_turn()
        assert state.active is c

    def test_wraps_around_and_increments_turn_count(self):
        a = make_combatant("A", dex=10)
        b = make_combatant("B", dex=8)
        state = BattleState(party=[a, b], enemies=[])
        state.build_turn_order()
        starting_turn = state.turn_count
        state.advance_turn()  # → b
        state.advance_turn()  # → a (wrap)
        assert state.active is a
        assert state.turn_count == starting_turn + 1

    def test_all_dead_does_not_loop_forever(self):
        a = make_combatant("A")
        state = BattleState(party=[a], enemies=[])
        state.build_turn_order()
        a.is_ko = True
        a.hp = 0
        # Should bail out after len(turn_order) iterations.
        state.advance_turn()


# ── update_floats ─────────────────────────────────────────────

class TestUpdateFloats:
    def test_purges_expired_floats(self):
        state = BattleState(party=[make_combatant("A")], enemies=[])
        # Fade rate is 300/sec. After 0.1s: short loses 30 from alpha (10→0,
        # purged); long loses 30 from 255 (still 225, kept).
        state.damage_floats.append(DamageFloat(text="short", x=0, y=0, color=(255, 0, 0), alpha=10))
        state.damage_floats.append(DamageFloat(text="long", x=0, y=0, color=(255, 0, 0), alpha=255))
        state.update_floats(0.1)
        assert [f.text for f in state.damage_floats] == ["long"]

    def test_advances_y_position(self):
        state = BattleState(party=[make_combatant("A")], enemies=[])
        f = DamageFloat(text="5", x=10, y=100, color=(255, 0, 0), vy=-40.0)
        state.damage_floats.append(f)
        state.update_floats(0.5)
        # y += int(vy * delta) = int(-40 * 0.5) = -20
        assert f.y == 80

    def test_no_floats_no_op(self):
        state = BattleState(party=[make_combatant("A")], enemies=[])
        state.update_floats(0.5)
        assert state.damage_floats == []


# ── alive/ko helpers ──────────────────────────────────────────

class TestAlivePartyHelpers:
    def test_alive_party_excludes_ko(self):
        a = make_combatant("A", hp=10)
        b = make_combatant("B", hp=0, is_ko=True)
        state = BattleState(party=[a, b], enemies=[])
        assert state.alive_party() == [a]

    def test_ko_party_only_returns_ko(self):
        a = make_combatant("A", hp=10)
        b = make_combatant("B", hp=0, is_ko=True)
        state = BattleState(party=[a, b], enemies=[])
        assert state.ko_party() == [b]

    def test_alive_enemies_excludes_dead(self):
        e1 = make_combatant("E1", hp=5, is_enemy=True)
        e2 = make_combatant("E2", hp=0, is_enemy=True, is_ko=True)
        state = BattleState(party=[], enemies=[e1, e2])
        assert state.alive_enemies() == [e1]

    def test_party_wiped_when_all_dead(self):
        state = BattleState(party=[make_combatant("A", hp=0, is_ko=True)], enemies=[])
        assert state.party_wiped is True

    def test_enemies_wiped_when_all_dead(self):
        state = BattleState(party=[], enemies=[make_combatant("E", hp=0, is_ko=True, is_enemy=True)])
        assert state.enemies_wiped is True
