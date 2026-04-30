# tests/unit/core/battle/test_battle_menu_builder.py

from __future__ import annotations

from unittest.mock import MagicMock

from engine.battle.combatant import Combatant
from engine.battle.battle_menu_builder import (
    build_spell_menu, build_item_menu, TARGET_MAP,
)


def make_combatant(name="Hero", mp=20, abilities=None) -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=100, hp_max=100, mp=mp, mp_max=50,
        atk=10, def_=5, mres=5, dex=10,
        is_enemy=False, boss=False,
        abilities=abilities or [], ai_data={},
    )


# ── build_spell_menu ─────────────────────────────────────────

class TestBuildSpellMenu:
    def test_filters_non_spell_types(self):
        active = make_combatant(abilities=[
            {"name": "Slash",  "type": "physical", "mp_cost": 0},
            {"name": "Cure",   "type": "heal",     "mp_cost": 4},
            {"name": "Fire",   "type": "spell",    "mp_cost": 8},
            {"name": "Tactics","type": "passive",  "mp_cost": 0},
        ])
        menu = build_spell_menu(active)
        labels = [m["label"] for m in menu]
        assert labels == ["Cure", "Fire"]

    def test_marks_unaffordable_disabled(self):
        active = make_combatant(mp=4, abilities=[
            {"name": "Cheap", "type": "heal",  "mp_cost": 4},
            {"name": "Pricey","type": "spell", "mp_cost": 99},
        ])
        menu = build_spell_menu(active)
        assert menu[0]["disabled"] is False
        assert menu[1]["disabled"] is True

    def test_carries_data_and_cost(self):
        ab = {"name": "Heal2", "type": "heal", "mp_cost": 6, "potency": 30}
        active = make_combatant(abilities=[ab])
        menu = build_spell_menu(active)
        assert menu[0]["data"] is ab
        assert menu[0]["mp_cost"] == 6

    def test_empty_abilities_returns_empty_menu(self):
        assert build_spell_menu(make_combatant(abilities=[])) == []

    def test_includes_all_spell_types(self):
        active = make_combatant(abilities=[
            {"name": "S",  "type": "spell",   "mp_cost": 1},
            {"name": "H",  "type": "heal",    "mp_cost": 1},
            {"name": "B",  "type": "buff",    "mp_cost": 1},
            {"name": "D",  "type": "debuff",  "mp_cost": 1},
            {"name": "U",  "type": "utility", "mp_cost": 1},
        ])
        menu = build_spell_menu(active)
        assert {m["label"] for m in menu} == {"S", "H", "B", "D", "U"}


# ── build_item_menu ──────────────────────────────────────────

class TestBuildItemMenu:
    def _entry(self, item_id: str, qty: int = 1):
        e = MagicMock()
        e.id = item_id
        e.qty = qty
        return e

    def _defn(self, target: str = "single_alive"):
        d = MagicMock()
        d.target = target
        return d

    def test_skips_items_without_def(self):
        repo = MagicMock(items=[self._entry("potion"), self._entry("chairleg")])
        handler = MagicMock()
        handler.get_def = lambda iid: self._defn() if iid == "potion" else None
        menu = build_item_menu(repo, handler)
        assert [m["data"]["id"] for m in menu] == ["potion"]

    def test_target_map_translation(self):
        repo = MagicMock(items=[
            self._entry("potion"), self._entry("phoenix"), self._entry("ether_all"),
        ])
        handler = MagicMock()
        targets = {"potion": "single_alive", "phoenix": "single_ko", "ether_all": "all_alive"}
        handler.get_def = lambda iid: self._defn(targets[iid])
        menu = build_item_menu(repo, handler)
        assert [m["data"]["target"] for m in menu] == [
            TARGET_MAP["single_alive"],
            TARGET_MAP["single_ko"],
            TARGET_MAP["all_alive"],
        ]

    def test_unknown_target_falls_back_to_single_ally(self):
        repo = MagicMock(items=[self._entry("weird")])
        handler = MagicMock()
        handler.get_def = lambda _id: self._defn("not_a_real_target")
        menu = build_item_menu(repo, handler)
        assert menu[0]["data"]["target"] == "single_ally"

    def test_label_titlecases_id(self):
        repo = MagicMock(items=[self._entry("hi_potion_plus")])
        handler = MagicMock()
        handler.get_def = lambda _id: self._defn()
        menu = build_item_menu(repo, handler)
        assert menu[0]["label"] == "Hi Potion Plus"

    def test_carries_qty(self):
        repo = MagicMock(items=[self._entry("potion", qty=7)])
        handler = MagicMock()
        handler.get_def = lambda _id: self._defn()
        menu = build_item_menu(repo, handler)
        assert menu[0]["qty"] == 7

    def test_no_handler_returns_empty(self):
        repo = MagicMock(items=[self._entry("potion")])
        assert build_item_menu(repo, None) == []
