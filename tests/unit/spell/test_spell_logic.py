# tests/unit/core/spell/test_spell_logic.py

import pytest

from engine.party.member_state import MemberState
from engine.spell.spell_logic import learned_spells, is_field_castable


CLASS_YAML = """\
abilities:
  - id: heal
    name: Heal
    type: heal
    unlock_level: 1
    mp_cost: 4
    heal_coeff: 1.5
    target: single_ally
  - id: fire_bolt
    name: Fire Bolt
    type: spell
    element: fire
    unlock_level: 1
    mp_cost: 4
    spell_coeff: 1.0
    target: single_enemy
  - id: cure
    name: Cure
    type: utility
    unlock_level: 3
    mp_cost: 5
    target: single_ally
  - id: power_strike
    name: Power Strike
    type: physical
    unlock_level: 2
    mp_cost: 0
    target: single_enemy
  - id: fireball
    name: Fireball
    type: spell
    element: fire
    unlock_level: 10
    mp_cost: 8
    spell_coeff: 1.4
    target: single_enemy
  - id: meteor
    name: Meteor
    type: spell
    element: fire
    unlock_level: 46
    unlock_flag: story_ultimate_fire
    mp_cost: 30
    spell_coeff: 2.5
    target: all_enemies
"""


@pytest.fixture
def classes_dir(tmp_path):
    d = tmp_path / "classes"
    d.mkdir()
    (d / "sorcerer.yaml").write_text(CLASS_YAML)
    return d


def make_member(level: int = 5, class_name: str = "sorcerer") -> MemberState:
    return MemberState(
        member_id="m", name="M", protagonist=False,
        class_name=class_name, level=level, exp=0, exp_next=100,
        hp=10, hp_max=10, mp=10, mp_max=10,
        str_=1, dex=1, con=1, int_=1, equipped={},
    )


class TestLearnedSpells:
    def test_excludes_physical_abilities(self, classes_dir):
        member = make_member(level=10)
        spells = learned_spells(member, classes_dir, flags=set())
        ids = [s["id"] for s in spells]
        assert "power_strike" not in ids  # type: physical

    def test_filters_by_level(self, classes_dir):
        member = make_member(level=5)
        ids = [s["id"] for s in learned_spells(member, classes_dir, flags=set())]
        assert "heal" in ids          # unlock_level 1
        assert "fire_bolt" in ids     # unlock_level 1
        assert "cure" in ids          # unlock_level 3
        assert "fireball" not in ids  # unlock_level 10

    def test_includes_higher_level_spells(self, classes_dir):
        member = make_member(level=15)
        ids = [s["id"] for s in learned_spells(member, classes_dir, flags=set())]
        assert "fireball" in ids

    def test_ultimate_gated_by_flag(self, classes_dir):
        member = make_member(level=50)
        ids = [s["id"] for s in learned_spells(member, classes_dir, flags=set())]
        assert "meteor" not in ids

    def test_ultimate_unlocked_with_flag(self, classes_dir):
        member = make_member(level=50)
        spells = learned_spells(
            member, classes_dir, flags={"story_ultimate_fire"},
        )
        ids = [s["id"] for s in spells]
        assert "meteor" in ids

    def test_ultimate_still_blocked_below_level(self, classes_dir):
        member = make_member(level=40)
        spells = learned_spells(
            member, classes_dir, flags={"story_ultimate_fire"},
        )
        ids = [s["id"] for s in spells]
        assert "meteor" not in ids

    def test_missing_class_file_raises(self, classes_dir):
        member = make_member(level=5, class_name="unknown")
        with pytest.raises(FileNotFoundError):
            learned_spells(member, classes_dir, flags=set())


class TestIsFieldCastable:
    def test_heal_is_castable(self):
        assert is_field_castable({"type": "heal", "target": "single_ally"})

    def test_utility_is_castable(self):
        assert is_field_castable({"type": "utility", "target": "single_ally"})

    def test_buff_on_self_or_party_is_castable(self):
        assert is_field_castable({"type": "buff", "target": "party"})

    def test_offensive_spell_is_not_castable(self):
        assert not is_field_castable(
            {"type": "spell", "target": "single_enemy"},
        )

    def test_debuff_is_not_castable(self):
        assert not is_field_castable(
            {"type": "debuff", "target": "all_enemies"},
        )

    def test_heal_with_enemy_target_is_not_castable(self):
        # Defense-in-depth: even heal-type entries shouldn't be castable
        # if they happen to target enemies.
        assert not is_field_castable(
            {"type": "heal", "target": "single_enemy"},
        )
