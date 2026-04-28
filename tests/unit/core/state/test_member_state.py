# tests/unit/core/state/test_member_state.py

import pytest

from engine.party.member_state import MemberState


def make_member(**overrides) -> MemberState:
    base = dict(
        member_id="hero", name="Hero", protagonist=True, class_name="hero",
        level=1, exp=0, hp=20, hp_max=20, mp=10, mp_max=10,
        str_=5, dex=5, con=5, int_=5,
        equipped={"weapon": "", "shield": "", "helmet": "", "body": "", "accessory": ""},
    )
    base.update(overrides)
    return MemberState(**base)


# ── Construction ─────────────────────────────────────────────

class TestConstruction:
    def test_basic_fields(self):
        m = make_member(name="Aric", level=3, exp=120)
        assert m.id == "hero"
        assert m.name == "Aric"
        assert m.level == 3
        assert m.exp == 120

    def test_stat_growth_starts_unloaded(self):
        m = make_member()
        assert m.stat_growth is None
        assert m.exp_base == 0
        assert m.exp_factor == 0.0
        assert m.equipment_slots == {}

    def test_exp_next_optional(self):
        assert make_member().exp_next == 0
        assert make_member(exp_next=999).exp_next == 999


# ── load_class_data ──────────────────────────────────────────

class TestLoadClassData:
    def test_loads_stat_growth_and_curve(self):
        m = make_member()
        m.load_class_data({
            "stat_growth": {
                "str": [3, 2, 3, 2, 3, 2, 3, 2, 3, 2],
                "dex": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                "con": [2, 3, 2, 3, 2, 3, 2, 3, 2, 3],
                "int": [1, 1, 2, 1, 1, 2, 1, 1, 2, 1],
            },
            "exp_base": 100,
            "exp_factor": 1.5,
            "equipment_slots": {"weapon": ["sword"], "shield": ["shield"]},
        })
        assert m.stat_growth["str"] == [3, 2, 3, 2, 3, 2, 3, 2, 3, 2]
        assert m.exp_base == 100
        assert m.exp_factor == 1.5
        assert m.equipment_slots == {"weapon": ["sword"], "shield": ["shield"]}

    def test_missing_stat_growth_key_raises(self):
        m = make_member()
        with pytest.raises(KeyError):
            m.load_class_data({"stat_growth": {"str": [1] * 10}})  # missing dex/con/int

    def test_equipment_slots_normalizes_none_lists(self):
        m = make_member()
        m.load_class_data({
            "stat_growth": {k: [1] * 10 for k in ("str", "dex", "con", "int")},
            "equipment_slots": {"weapon": None, "shield": ["shield"]},
        })
        assert m.equipment_slots == {"weapon": [], "shield": ["shield"]}

    def test_load_stat_growth_alias(self):
        # Backward-compat alias for legacy callers.
        m = make_member()
        m.load_stat_growth({
            "stat_growth": {k: [1] * 10 for k in ("str", "dex", "con", "int")},
        })
        assert m.stat_growth is not None

    def test_omitted_exp_curve_keeps_defaults(self):
        m = make_member()
        m.load_class_data({
            "stat_growth": {k: [1] * 10 for k in ("str", "dex", "con", "int")},
        })
        assert m.exp_base == 0
        assert m.exp_factor == 0.0


# ── repr ─────────────────────────────────────────────────────

class TestRepr:
    def test_repr_marks_protagonist(self):
        assert "[protagonist]" in repr(make_member(protagonist=True))

    def test_repr_no_marker_for_non_protagonist(self):
        assert "[protagonist]" not in repr(make_member(protagonist=False))
