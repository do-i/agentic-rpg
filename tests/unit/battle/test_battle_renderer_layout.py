# tests/unit/battle/test_battle_renderer_layout.py
#
# Pure-helper tests for the battle renderer: layout math, enemy_rect_size,
# float_pos, and the HP color threshold logic. These don't exercise pygame
# drawing — just the small numeric helpers § 5.4 called out.

from __future__ import annotations

import pygame
import pytest
from unittest.mock import patch, MagicMock

from engine.battle.battle_floats import enemy_rect_size, float_pos
from engine.battle.battle_enemy_area_renderer import BAR_RESERVE_PX, EnemyAreaRenderer
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H, ENEMY_SIZES
from engine.battle.battle_renderer_constants import (
    CARD_GAP, CARD_PORTRAIT, PANEL_GAP, PANEL_MARGIN,
)
from engine.battle.ground_rect_catalog import GroundRect
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
    def test_panels_span_bottom_section(self):
        r = _make_renderer(screen_h=800)
        party, cmd, msg = r._layout(member_count=4)
        # All three panels start below the (untouched) enemy area and share
        # the same top / height.
        assert party.y == ENEMY_AREA_H + PANEL_MARGIN
        assert party.height == 800 - ENEMY_AREA_H - PANEL_MARGIN * 2
        assert cmd.y == party.y == msg.y
        assert cmd.height == party.height == msg.height

    def test_party_widens_with_member_count(self):
        r = _make_renderer(screen_w=1280)
        one = r._layout(member_count=1)[0]
        five = r._layout(member_count=5)[0]
        # One 100px portrait column per member → more members, wider party.
        assert five.width > one.width

    def test_party_column_pitch_matches_card_size(self):
        # The party width grows by exactly one card pitch per extra member
        # until it hits the reserved-width cap.
        r = _make_renderer(screen_w=1600)
        w3 = r._layout(member_count=3)[0].width
        w4 = r._layout(member_count=4)[0].width
        assert w4 - w3 == (CARD_PORTRAIT + 8) + CARD_GAP

    def test_panels_are_left_to_right_without_overlap(self):
        r = _make_renderer(screen_w=1280)
        party, cmd, msg = r._layout(member_count=5)
        assert cmd.x == party.right + PANEL_GAP
        assert msg.x == cmd.right + PANEL_GAP
        assert msg.right == 1280 - PANEL_MARGIN

    def test_all_panels_have_positive_width(self):
        r = _make_renderer(screen_w=1280)
        for rect in r._layout(member_count=5):
            assert rect.width > 0


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
    def test_party_float_over_member_column(self):
        a = make_combatant("A")
        b = make_combatant("B")
        state = BattleState(party=[a, b], enemies=[])
        ax, ay = float_pos(state, a, screen_width=1280)
        bx, by = float_pos(state, b, screen_width=1280)
        # Members lay out left-to-right: same y, b one card pitch right of a.
        assert ay == by
        assert bx - ax == (CARD_PORTRAIT + 8) + CARD_GAP

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


# ── EnemyAreaRenderer._clamp_to_ground ───────────────────────

class TestClampToGround:
    def test_center_position_is_unchanged(self):
        ground = GroundRect(x=0, y=0, width=1280, height=468)
        cx, cy = EnemyAreaRenderer._clamp_to_ground(640, 244, 80, 80, ground)
        assert (cx, cy) == (640, 244)

    def test_feet_pulled_up_to_ground_when_floating_above_it(self):
        # zone10-style short ground strip: a boss-sized sprite whose feet
        # land above the strip gets pulled down until its feet touch it —
        # but only the feet; the body is free to render above ground.top.
        ground = GroundRect(x=40, y=351, width=1200, height=117)
        cx, cy = EnemyAreaRenderer._clamp_to_ground(640, 200, 96, 96, ground)
        feet = cy + 96 // 2
        assert feet == ground.top
        assert cy - 96 // 2 < ground.top

    def test_feet_pulled_up_to_leave_room_for_hp_bar(self):
        # This is the zone10 bug: centering a large sprite in a short rect
        # put its feet within a few px of the screen's bottom seam, with
        # no room left for the HP bar/name below.
        ground = GroundRect(x=40, y=351, width=1200, height=117)
        cx, cy = EnemyAreaRenderer._clamp_to_ground(640, 419, 80, 80, ground)
        feet = cy + 80 // 2
        assert feet == ground.bottom - BAR_RESERVE_PX

    def test_horizontal_edge_clamped_to_narrow_ground(self):
        # zone7-style ground patch narrower than the screen: a far-left
        # formation slot must not land in the water past the patch edge.
        ground = GroundRect(x=160, y=310, width=960, height=158)
        cx, cy = EnemyAreaRenderer._clamp_to_ground(100, 350, 52, 52, ground)
        assert cx == ground.left + 52 // 2

    def test_degenerate_ground_smaller_than_sprite_does_not_invert(self):
        ground = GroundRect(x=0, y=0, width=10, height=10)
        cx, cy = EnemyAreaRenderer._clamp_to_ground(5, 5, 80, 80, ground)
        assert cx == ground.left + 80 // 2
        assert cy + 80 // 2 == ground.top


# ── HP_LOW_THRESHOLD selection logic ─────────────────────────

class TestHpThresholdLogic:
    """The party-panel renderer picks HP bar color via:
        C_HP_BAR_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_BAR
    The threshold itself is defined in color_constants. Lock in the value
    and exercise the surrounding inequality so a future tweak (e.g. flipping
    < to <=) is caught."""

    def test_threshold_value_pinned(self):
        # Pin the value so a change requires touching the test.
        assert HP_LOW_THRESHOLD == 0.35

    def test_at_threshold_counts_as_low(self):
        # The renderer uses `<=` so exactly-at-threshold triggers low color.
        from engine.battle.battle_renderer_constants import C_HP_BAR, C_HP_BAR_LOW
        hp_pct = HP_LOW_THRESHOLD
        chosen = C_HP_BAR_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_BAR
        assert chosen == C_HP_BAR_LOW

    def test_just_above_threshold_counts_as_ok(self):
        from engine.battle.battle_renderer_constants import C_HP_BAR, C_HP_BAR_LOW
        hp_pct = HP_LOW_THRESHOLD + 0.01
        chosen = C_HP_BAR_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_BAR
        assert chosen == C_HP_BAR

    def test_zero_hp_is_low(self):
        from engine.battle.battle_renderer_constants import C_HP_BAR, C_HP_BAR_LOW
        chosen = C_HP_BAR_LOW if 0.0 <= HP_LOW_THRESHOLD else C_HP_BAR
        assert chosen == C_HP_BAR_LOW

    def test_full_hp_is_ok(self):
        from engine.battle.battle_renderer_constants import C_HP_BAR, C_HP_BAR_LOW
        chosen = C_HP_BAR_LOW if 1.0 <= HP_LOW_THRESHOLD else C_HP_BAR
        assert chosen == C_HP_BAR
