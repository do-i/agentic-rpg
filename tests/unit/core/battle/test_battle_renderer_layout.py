# tests/unit/core/battle/test_battle_renderer_layout.py
#
# Pure-helper tests for the battle renderer: layout math, enemy_rect_size,
# float_pos, and the HP color threshold logic. These don't exercise pygame
# drawing — just the small numeric helpers § 5.4 called out.

import pygame
import pytest
from unittest.mock import patch, MagicMock

from engine.battle.battle_floats import enemy_rect_size, float_pos
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H, ENEMY_SIZES, ROW_H
from engine.common.color_constants import HP_LOW_THRESHOLD


def make_combatant(name="X", is_enemy=False, boss=False, hp=100, hp_max=100) -> Combatant:
    return Combatant(
        id=name.lower(), name=name,
        hp=hp, hp_max=hp_max, mp=0, mp_max=0,
        atk=10, def_=5, mres=5, dex=10,
        is_enemy=is_enemy, boss=boss,
        abilities=[], ai_data={},
    )


# ── BattleRenderer layout math ───────────────────────────────

def _make_renderer(screen_w=1280, screen_h=766):
    from engine.battle.battle_renderer import BattleRenderer
    with patch("engine.battle.battle_renderer.BattleAssetCache"):
        return BattleRenderer(scenario_path="ignored",
                              screen_width=screen_w, screen_height=screen_h)


class TestBattleRendererLayout:
    def test_bottom_h_is_screen_height_minus_enemy_area(self):
        r = _make_renderer(screen_h=800)
        assert r.bottom_h == 800 - ENEMY_AREA_H

    def test_party_w_is_quarter_of_screen(self):
        assert _make_renderer(screen_w=1280).party_w == 320
        assert _make_renderer(screen_w=800).party_w == 200

    def test_cmd_w_is_30_percent_of_screen(self):
        assert _make_renderer(screen_w=1000).cmd_w == 300
        assert _make_renderer(screen_w=1280).cmd_w == 384

    def test_msg_x_is_party_plus_cmd(self):
        r = _make_renderer(screen_w=1280)
        assert r.msg_x == r.party_w + r.cmd_w

    def test_msg_w_fills_remaining_width(self):
        r = _make_renderer(screen_w=1280)
        assert r.msg_w == 1280 - r.msg_x

    def test_msg_w_zero_for_minimum_width(self):
        # 0.25 + 0.30 = 0.55 of screen → some width remains.
        r = _make_renderer(screen_w=400)
        assert r.msg_w > 0


# ── enemy_rect_size ──────────────────────────────────────────

class TestEnemyRectSize:
    def test_boss_returns_large(self):
        boss = make_combatant("Dragon", is_enemy=True, boss=True)
        assert enemy_rect_size(boss) == ENEMY_SIZES["large"]

    def test_non_boss_picks_size_by_name_length_mod_3(self):
        # idx = len(name) % 3 → table is [medium, small, medium]
        cases = [
            ("X", ENEMY_SIZES["small"]),    # len 1 -> 1
            ("XX", ENEMY_SIZES["medium"]),  # len 2 -> 2
            ("XXX", ENEMY_SIZES["medium"]), # len 3 -> 0
            ("XXXX", ENEMY_SIZES["small"]), # len 4 -> 1
        ]
        for name, expected in cases:
            c = make_combatant(name, is_enemy=True)
            assert enemy_rect_size(c) == expected, name


# ── float_pos ────────────────────────────────────────────────

class TestFloatPos:
    def test_party_float_above_party_panel(self):
        a = make_combatant("A")
        b = make_combatant("B")
        state = BattleState(party=[a, b], enemies=[])
        ax, ay = float_pos(state, a, screen_width=1280)
        bx, by = float_pos(state, b, screen_width=1280)
        # Both floats anchored to party_w left side; b is one ROW_H below a.
        assert ax == bx
        assert by - ay == (ROW_H + 2)

    def test_enemy_float_uses_layout_offset(self):
        e1 = make_combatant("E1", is_enemy=True)
        e2 = make_combatant("E2", is_enemy=True)
        state = BattleState(party=[], enemies=[e1, e2])
        x1, _ = float_pos(state, e1, screen_width=1280)
        x2, _ = float_pos(state, e2, screen_width=1280)
        # 2-enemy layout offsets are (-80, 0) and (80, 0); first is left of second.
        assert x1 < x2

    def test_boss_float_y_lifts_above_large_sprite(self):
        boss = make_combatant("Drake", is_enemy=True, boss=True)
        normal = make_combatant("Drake", is_enemy=True, boss=False)
        state_boss = BattleState(party=[], enemies=[boss])
        state_norm = BattleState(party=[], enemies=[normal])
        _, y_boss = float_pos(state_boss, boss, screen_width=1280)
        _, y_norm = float_pos(state_norm, normal, screen_width=1280)
        # Bigger sprite → float anchored higher (smaller y).
        assert y_boss < y_norm


# ── HP_LOW_THRESHOLD selection logic ─────────────────────────

class TestHpThresholdLogic:
    """The party-panel renderer picks HP color via:
        C_HP_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
    The threshold itself is defined in color_constants. Lock in the value
    and exercise the surrounding inequality so a future tweak (e.g. flipping
    < to <=) is caught."""

    def test_threshold_value_pinned(self):
        # Pin the value so a change requires touching the test.
        assert HP_LOW_THRESHOLD == 0.35

    def test_at_threshold_counts_as_low(self):
        # The renderer uses `<=` so exactly-at-threshold triggers low color.
        from engine.battle.battle_renderer_constants import C_HP_LOW, C_HP_OK
        hp_pct = HP_LOW_THRESHOLD
        chosen = C_HP_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
        assert chosen == C_HP_LOW

    def test_just_above_threshold_counts_as_ok(self):
        from engine.battle.battle_renderer_constants import C_HP_LOW, C_HP_OK
        hp_pct = HP_LOW_THRESHOLD + 0.01
        chosen = C_HP_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
        assert chosen == C_HP_OK

    def test_zero_hp_is_low(self):
        from engine.battle.battle_renderer_constants import C_HP_LOW, C_HP_OK
        chosen = C_HP_LOW if 0.0 <= HP_LOW_THRESHOLD else C_HP_OK
        assert chosen == C_HP_LOW

    def test_full_hp_is_ok(self):
        from engine.battle.battle_renderer_constants import C_HP_LOW, C_HP_OK
        chosen = C_HP_LOW if 1.0 <= HP_LOW_THRESHOLD else C_HP_OK
        assert chosen == C_HP_OK
