# tests/unit/core/battle/test_battle_rewards.py

import pytest
from unittest.mock import patch
from engine.core.battle.battle_rewards import (
    RewardCalculator, exp_required, LevelUpResult,
    EXP_CAP, LEVEL_CAP, _weighted_pick,
)
from engine.core.battle.combatant import Combatant
from engine.core.state.party_state import PartyState, MemberState


STAT_GROWTH = {
    "stat_growth": {
        "str": [3, 2, 3, 2, 3, 2, 3, 2, 3, 2],
        "dex": [2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
        "con": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        "int": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    }
}


def _make_member(name="Aric", level=1, exp=0, hp=50, class_name="hero") -> MemberState:
    m = MemberState(
        member_id=name.lower(), name=name, protagonist=True,
        class_name=class_name, level=level, exp=exp,
        hp=hp, hp_max=50, mp=20, mp_max=20,
        str_=10, dex=8, con=9, int_=6, equipped={},
    )
    m.load_stat_growth(STAT_GROWTH)
    return m


def _make_enemy(exp_yield=100) -> Combatant:
    return Combatant(
        id="slime_01", name="Slime", is_enemy=True,
        hp=10, hp_max=10, mp=0, mp_max=0,
        atk=5, def_=3, mres=2, dex=3,
        exp_yield=exp_yield,
    )


def _party_with(members: list[MemberState]) -> PartyState:
    p = PartyState()
    for m in members:
        p.add_member(m)
    return p


class TestExpRequired:
    def test_level_1_hero(self):
        assert exp_required("hero", 1) == 100

    def test_level_2_hero(self):
        assert exp_required("hero", 2) == 400

    def test_unknown_class_uses_default_base(self):
        assert exp_required("unknown", 1) == 100

    def test_case_insensitive(self):
        assert exp_required("Hero", 2) == exp_required("hero", 2)


class TestRewardCalculatorBasic:
    def test_total_exp_is_sum_of_enemy_yields(self):
        calc = RewardCalculator()
        enemies = [_make_enemy(100), _make_enemy(50)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert rewards.total_exp == 150

    def test_exp_split_evenly_among_living(self):
        calc = RewardCalculator()
        enemies = [_make_enemy(100)]
        m1 = _make_member("A")
        m2 = _make_member("B")
        party = _party_with([m1, m2])
        rewards = calc.calculate(enemies, party)
        assert rewards.member_results[0].exp_gained == 50
        assert rewards.member_results[1].exp_gained == 50

    def test_ko_members_get_zero_exp(self):
        calc = RewardCalculator()
        enemies = [_make_enemy(100)]
        ko = _make_member("Dead", hp=0)
        alive = _make_member("Alive")
        party = _party_with([ko, alive])
        rewards = calc.calculate(enemies, party)
        assert rewards.member_results[0].exp_gained == 0
        assert rewards.member_results[1].exp_gained == 100

    def test_boss_flag_forwarded(self):
        calc = RewardCalculator()
        enemies = [_make_enemy(10)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party, boss_flag="boss_defeated")
        assert rewards.boss_flag == "boss_defeated"


class TestLevelUp:
    def test_level_up_occurs(self):
        calc = RewardCalculator()
        # hero level 2 needs exp_required("hero", 2) = 400
        m = _make_member(level=1, exp=350)
        enemies = [_make_enemy(100)]
        party = _party_with([m])
        rewards = calc.calculate(enemies, party)
        assert len(rewards.member_results[0].level_ups) >= 1
        assert m.level == 2

    def test_level_up_increases_stats(self):
        m = _make_member(level=1, exp=0)
        old_str = m.str_
        calc = RewardCalculator()
        # Give enough EXP for a level-up
        enemies = [_make_enemy(500)]
        party = _party_with([m])
        calc.calculate(enemies, party)
        assert m.str_ > old_str

    def test_hp_mp_restored_on_level_up(self):
        m = _make_member(level=1, exp=350, hp=1)
        calc = RewardCalculator()
        enemies = [_make_enemy(100)]
        party = _party_with([m])
        calc.calculate(enemies, party)
        assert m.hp == m.hp_max
        assert m.mp == m.mp_max

    def test_no_level_up_at_cap(self):
        m = _make_member(level=LEVEL_CAP, exp=0)
        calc = RewardCalculator()
        enemies = [_make_enemy(99999)]
        party = _party_with([m])
        rewards = calc.calculate(enemies, party)
        assert len(rewards.member_results[0].level_ups) == 0
        assert m.level == LEVEL_CAP


def _make_enemy_with_drops(exp_yield=100, drops=None) -> Combatant:
    return Combatant(
        id="slime_01", name="Slime", is_enemy=True,
        hp=10, hp_max=10, mp=0, mp_max=0,
        atk=5, def_=3, mres=2, dex=3,
        exp_yield=exp_yield,
        drops=drops or {},
    )


class TestLoot:
    def test_no_drops_returns_empty(self):
        calc = RewardCalculator()
        enemies = [_make_enemy()]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert rewards.loot.mc_drops == []
        assert rewards.loot.item_drops == []

    def test_mc_drops_from_enemy_yaml(self):
        calc = RewardCalculator()
        drops = {"mc": [{"size": "S", "qty": 2}]}
        enemies = [_make_enemy_with_drops(drops=drops)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert len(rewards.loot.mc_drops) == 1
        assert rewards.loot.mc_drops[0] == {"size": "S", "qty": 2}

    def test_mc_drops_aggregate_same_size(self):
        calc = RewardCalculator()
        drops = {"mc": [{"size": "S", "qty": 1}]}
        enemies = [_make_enemy_with_drops(drops=drops), _make_enemy_with_drops(drops=drops)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert len(rewards.loot.mc_drops) == 1
        assert rewards.loot.mc_drops[0] == {"size": "S", "qty": 2}

    def test_mc_drops_different_sizes(self):
        calc = RewardCalculator()
        e1 = _make_enemy_with_drops(drops={"mc": [{"size": "S", "qty": 1}]})
        e2 = _make_enemy_with_drops(drops={"mc": [{"size": "M", "qty": 1}]})
        party = _party_with([_make_member()])
        rewards = calc.calculate([e1, e2], party)
        sizes = {d["size"] for d in rewards.loot.mc_drops}
        assert sizes == {"S", "M"}

    def test_mc_multiple_entries_per_enemy(self):
        calc = RewardCalculator()
        drops = {"mc": [{"size": "L", "qty": 2}, {"size": "XL", "qty": 1}]}
        enemies = [_make_enemy_with_drops(drops=drops)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        mc_map = {d["size"]: d["qty"] for d in rewards.loot.mc_drops}
        assert mc_map == {"L": 2, "XL": 1}

    def test_loot_pool_rolls_item(self):
        calc = RewardCalculator()
        drops = {"loot": [{"pool": [
            {"item": "rat_tail", "weight": 80},
            {"item": "rat_hide", "weight": 20},
        ]}]}
        enemies = [_make_enemy_with_drops(drops=drops)]
        party = _party_with([_make_member()])

        with patch("engine.core.battle.battle_rewards.random.choices",
                   return_value=["rat_tail"]):
            rewards = calc.calculate(enemies, party)

        assert len(rewards.loot.item_drops) == 1
        assert rewards.loot.item_drops[0]["id"] == "rat_tail"
        assert rewards.loot.item_drops[0]["qty"] == 1
        assert rewards.loot.item_drops[0]["name"] == "Rat Tail"

    def test_loot_duplicate_items_aggregate(self):
        calc = RewardCalculator()
        drops = {"loot": [
            {"pool": [{"item": "bat_wing", "weight": 100}]},
        ]}
        # Two enemies both drop bat_wing
        enemies = [
            _make_enemy_with_drops(drops=drops),
            _make_enemy_with_drops(drops=drops),
        ]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert len(rewards.loot.item_drops) == 1
        assert rewards.loot.item_drops[0]["id"] == "bat_wing"
        assert rewards.loot.item_drops[0]["qty"] == 2

    def test_empty_loot_pool_no_item(self):
        calc = RewardCalculator()
        drops = {"loot": [{"pool": []}]}
        enemies = [_make_enemy_with_drops(drops=drops)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert rewards.loot.item_drops == []

    def test_combined_mc_and_loot(self):
        calc = RewardCalculator()
        drops = {
            "mc": [{"size": "XS", "qty": 3}],
            "loot": [{"pool": [{"item": "golem_core", "weight": 100}]}],
        }
        enemies = [_make_enemy_with_drops(drops=drops)]
        party = _party_with([_make_member()])
        rewards = calc.calculate(enemies, party)
        assert len(rewards.loot.mc_drops) == 1
        assert rewards.loot.mc_drops[0] == {"size": "XS", "qty": 3}
        assert len(rewards.loot.item_drops) == 1
        assert rewards.loot.item_drops[0]["id"] == "golem_core"


class TestWeightedPick:
    def test_empty_pool_returns_none(self):
        assert _weighted_pick([]) is None

    def test_single_item_always_picked(self):
        pool = [{"item": "only_one", "weight": 50}]
        assert _weighted_pick(pool) == "only_one"

    def test_respects_weights(self):
        pool = [
            {"item": "common", "weight": 90},
            {"item": "rare", "weight": 10},
        ]
        results = [_weighted_pick(pool) for _ in range(200)]
        assert "common" in results
        # rare should appear at least once in 200 draws with 10% chance
        assert "rare" in results
