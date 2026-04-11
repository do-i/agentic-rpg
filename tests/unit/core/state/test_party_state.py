# tests/unit/core/state/test_party_state.py

import pytest
from engine.common.member_state import MemberState
from engine.common.party_state import PartyState
from engine.common.service.party_state import (
    calc_exp_next, stat_gain_at, recalc_exp_next, exp_pct, LEVEL_CAP,
)


STAT_GROWTH = {
    "stat_growth": {
        "str": [3, 2, 3, 2, 3, 2, 3, 2, 3, 2],
        "dex": [2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
        "con": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        "int": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    }
}


def _make_member(name="Aric", protagonist=True, class_name="hero", level=1) -> MemberState:
    return MemberState(
        member_id=name.lower(), name=name, protagonist=protagonist,
        class_name=class_name, level=level, exp=0,
        hp=50, hp_max=50, mp=20, mp_max=20,
        str_=10, dex=8, con=9, int_=6, equipped={"weapon": "Iron Sword"},
    )


# -- calc_exp_next --

class TestCalcExpNext:
    def test_returns_positive_for_low_level(self):
        assert calc_exp_next("hero", 1) > 0

    def test_returns_zero_at_cap(self):
        assert calc_exp_next("hero", LEVEL_CAP) == 0

    def test_increases_with_level(self):
        assert calc_exp_next("hero", 10) > calc_exp_next("hero", 5)

    def test_different_classes_differ(self):
        assert calc_exp_next("warrior", 5) != calc_exp_next("rogue", 5)


# -- MemberState --

class TestMemberStateStatGrowth:
    def test_stat_gain_returns_zero_without_load(self):
        m = _make_member()
        assert stat_gain_at(m, "str", 1) == 0

    def test_stat_gain_after_load(self):
        m = _make_member()
        m.load_stat_growth(STAT_GROWTH)
        assert stat_gain_at(m, "str", 1) == 3  # index 0

    def test_stat_gain_cycles_modulo(self):
        m = _make_member()
        m.load_stat_growth(STAT_GROWTH)
        # level 11 -> index (11-1) % 10 = 0 -> same as level 1
        assert stat_gain_at(m, "str", 11) == stat_gain_at(m, "str", 1)

    def test_recalc_exp_next(self):
        m = _make_member(level=1)
        old = m.exp_next
        m.level = 5
        recalc_exp_next(m)
        assert m.exp_next > old

    def test_repr_includes_protagonist_tag(self):
        m = _make_member(protagonist=True)
        assert "[protagonist]" in repr(m)

    def test_repr_excludes_tag_for_non_protagonist(self):
        m = _make_member(protagonist=False)
        assert "[protagonist]" not in repr(m)


# -- PartyState --

class TestPartyState:
    def test_starts_empty(self):
        p = PartyState()
        assert p.members == []

    def test_add_member(self):
        p = PartyState()
        m = _make_member()
        p.add_member(m)
        assert len(p.members) == 1

    def test_members_returns_copy(self):
        p = PartyState()
        p.add_member(_make_member())
        members = p.members
        members.clear()
        assert len(p.members) == 1

    def test_protagonist_property(self):
        p = PartyState()
        p.add_member(_make_member("Aric", protagonist=True))
        p.add_member(_make_member("Elise", protagonist=False))
        assert p.protagonist.name == "Aric"

    def test_protagonist_none_when_empty(self):
        p = PartyState()
        assert p.protagonist is None

    def test_set_protagonist_name(self):
        p = PartyState()
        p.add_member(_make_member("Aric", protagonist=True))
        p.set_protagonist_name("Hero")
        assert p.protagonist.name == "Hero"

    def test_set_protagonist_name_no_protagonist(self):
        p = PartyState()
        p.add_member(_make_member("Elise", protagonist=False))
        p.set_protagonist_name("Hero")  # should not raise
        assert p.members[0].name == "Elise"

    def test_repr(self):
        p = PartyState()
        assert "PartyState" in repr(p)
