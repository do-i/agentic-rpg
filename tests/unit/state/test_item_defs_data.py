# tests/unit/core/state/test_item_defs_data.py

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from engine.item.item_defs_data import FieldItemDef, UseResult


class TestFieldItemDef:
    def test_minimum_construction(self):
        d = FieldItemDef(id="potion", effect="restore_hp", target="single_alive")
        assert d.amount == 0
        assert d.cures == []
        assert d.revive_hp_pct == 0.0
        assert d.consumable is True

    def test_frozen(self):
        d = FieldItemDef(id="potion", effect="restore_hp", target="single_alive")
        with pytest.raises(FrozenInstanceError):
            d.amount = 50

    def test_default_cures_is_independent(self):
        a = FieldItemDef(id="a", effect="cure", target="single_alive")
        b = FieldItemDef(id="b", effect="cure", target="single_alive")
        # Both are frozen, but the default lists must not be shared.
        assert a.cures is not b.cures

    def test_revive_carries_pct(self):
        d = FieldItemDef(
            id="phoenix_down", effect="revive", target="single_ko",
            revive_hp_pct=0.25,
        )
        assert d.revive_hp_pct == 0.25

    def test_keyitem_marked_non_consumable(self):
        d = FieldItemDef(id="veil_breaker", effect="revive",
                         target="single_alive", consumable=False)
        assert d.consumable is False


class TestUseResult:
    def test_success_no_warning(self):
        r = UseResult(success=True)
        assert r.success is True
        assert r.warning == ""
        assert r.messages == []

    def test_messages_default_independent(self):
        a = UseResult(success=True)
        b = UseResult(success=True)
        assert a.messages is not b.messages

    def test_frozen(self):
        r = UseResult(success=True)
        with pytest.raises(FrozenInstanceError):
            r.success = False

    def test_warning_field(self):
        r = UseResult(success=True, warning="full HP")
        assert r.warning == "full HP"
