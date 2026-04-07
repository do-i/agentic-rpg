# tests/unit/core/scenes/test_status_logic.py

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from engine.state.party_state import MemberState
from engine.state.status_logic import (
    field_spells, valid_targets, apply_spell, apply_spell_all,
    load_class_data, FIELD_SPELL_TYPES,
)


def make_member(name="Aric", hp=100, hp_max=100, mp=50, mp_max=80,
                level=5, class_name="Hero", int_=16) -> MemberState:
    return MemberState(
        member_id=name.lower(), name=name, protagonist=False,
        class_name=class_name, level=level,
        exp=0, exp_next=1000,
        hp=hp, hp_max=hp_max, mp=mp, mp_max=mp_max,
        str_=10, dex=8, con=9, int_=int_,
        equipped={},
    )


# ── load_class_data ───────────────────────────────────────────

class TestLoadClassData:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_class_data(tmp_path, "nonexistent")
        assert result == {}

    def test_loads_yaml(self, tmp_path):
        (tmp_path / "hero.yaml").write_text("abilities:\n  - name: Heal\n    type: heal\n")
        result = load_class_data(tmp_path, "hero")
        assert result["abilities"][0]["name"] == "Heal"


# ── field_spells ──────────────────────────────────────────────

class TestFieldSpells:
    def test_filters_field_usable(self, tmp_path):
        classes_dir = tmp_path / "data" / "classes"
        classes_dir.mkdir(parents=True)
        (classes_dir / "cleric.yaml").write_text("""
abilities:
  - name: Heal
    type: heal
    unlock_level: 1
  - name: Fire
    type: spell
    unlock_level: 1
  - name: Cure
    type: utility
    unlock_level: 1
  - name: Barrier
    type: buff
    unlock_level: 1
""")
        member = make_member(class_name="cleric", level=5)
        result = field_spells(member, str(tmp_path))

        names = [s["name"] for s in result]
        assert "Heal" in names
        assert "Cure" in names
        assert "Barrier" in names
        assert "Fire" not in names

    def test_respects_unlock_level(self, tmp_path):
        classes_dir = tmp_path / "data" / "classes"
        classes_dir.mkdir(parents=True)
        (classes_dir / "cleric.yaml").write_text("""
abilities:
  - name: Heal
    type: heal
    unlock_level: 1
  - name: Mega Heal
    type: heal
    unlock_level: 20
""")
        member = make_member(class_name="cleric", level=5)
        result = field_spells(member, str(tmp_path))

        names = [s["name"] for s in result]
        assert "Heal" in names
        assert "Mega Heal" not in names

    def test_missing_class_file_returns_empty(self, tmp_path):
        classes_dir = tmp_path / "data" / "classes"
        classes_dir.mkdir(parents=True)
        member = make_member(class_name="nonexistent", level=5)
        result = field_spells(member, str(tmp_path))
        assert result == []


# ── valid_targets ─────────────────────────────────────────────

class TestValidTargets:
    def test_single_ally_returns_alive(self):
        alive = make_member("Alive", hp=50)
        dead = make_member("Dead", hp=0)
        result = valid_targets({"target": "single_ally"}, [alive, dead])
        assert result == [alive]

    def test_single_ko_returns_dead(self):
        alive = make_member("Alive", hp=50)
        dead = make_member("Dead", hp=0)
        result = valid_targets({"target": "single_ko"}, [alive, dead])
        assert result == [dead]

    def test_revive_targets_dead(self):
        alive = make_member("Alive", hp=50)
        dead = make_member("Dead", hp=0)
        result = valid_targets({"revive_hp_pct": 0.5}, [alive, dead])
        assert result == [dead]

    def test_default_target_single_ally(self):
        alive = make_member("Alive", hp=50)
        result = valid_targets({}, [alive])
        assert result == [alive]


# ── apply_spell ───────────────────────────────────────────────

class TestApplySpell:
    def test_heal(self):
        caster = make_member("Caster", mp=50, int_=20)
        target = make_member("Target", hp=50, hp_max=100)
        spell = {"name": "Heal", "type": "heal", "heal_coeff": 2.0, "mp_cost": 10}

        msg = apply_spell(spell, caster, target)

        assert target.hp == 90  # 50 + int(20 * 2.0)
        assert caster.mp == 40  # 50 - 10
        assert "healed 40 HP" in msg

    def test_heal_caps_at_max(self):
        caster = make_member("Caster", mp=50, int_=100)
        target = make_member("Target", hp=90, hp_max=100)
        spell = {"name": "Heal", "type": "heal", "heal_coeff": 1.0, "mp_cost": 5}

        msg = apply_spell(spell, caster, target)

        assert target.hp == 100
        assert "healed 10 HP" in msg

    def test_revive(self):
        caster = make_member("Caster", mp=50)
        target = make_member("Target", hp=0, hp_max=200)
        spell = {"name": "Raise", "type": "heal", "revive_hp_pct": 0.5, "mp_cost": 20}

        msg = apply_spell(spell, caster, target)

        assert target.hp == 100
        assert caster.mp == 30
        assert "revived" in msg

    def test_utility(self):
        caster = make_member("Caster", mp=50)
        target = make_member("Target")
        spell = {"name": "Esuna", "type": "utility", "mp_cost": 5}

        msg = apply_spell(spell, caster, target)

        assert "cured" in msg
        assert caster.mp == 45

    def test_buff(self):
        caster = make_member("Caster", mp=50)
        target = make_member("Target")
        spell = {"name": "Protect", "type": "buff", "mp_cost": 8}

        msg = apply_spell(spell, caster, target)

        assert "Protect cast" in msg
        assert caster.mp == 42

    def test_unknown_type(self):
        caster = make_member("Caster", mp=50)
        target = make_member("Target")
        spell = {"name": "Mystery", "type": "unknown", "mp_cost": 3}

        msg = apply_spell(spell, caster, target)

        assert "Mystery used" in msg


# ── apply_spell_all ───────────────────────────────────────────

class TestApplySpellAll:
    def test_heals_all_alive(self):
        caster = make_member("Caster", mp=80, int_=10)
        m1 = make_member("A", hp=50, hp_max=100)
        m2 = make_member("B", hp=70, hp_max=100)
        dead = make_member("C", hp=0, hp_max=100)
        spell = {"name": "Heal All", "type": "heal", "heal_coeff": 2.0, "mp_cost": 20}

        msg = apply_spell_all(spell, caster, [m1, m2, dead])

        assert m1.hp == 70  # 50 + 20
        assert m2.hp == 90  # 70 + 20
        assert dead.hp == 0  # skipped
        assert caster.mp == 60
        assert "Party healed 40 HP" in msg

    def test_deducts_mp_once(self):
        caster = make_member("Caster", mp=30, int_=5)
        m1 = make_member("A", hp=90, hp_max=100)
        spell = {"name": "Heal All", "type": "heal", "heal_coeff": 1.0, "mp_cost": 10}

        apply_spell_all(spell, caster, [m1])

        assert caster.mp == 20  # only deducted once
