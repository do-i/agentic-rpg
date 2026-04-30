# tests/unit/world/test_portal.py

from __future__ import annotations

from engine.world.portal_data import Portal
from engine.world.position_data import Position


def _portal(x=100, y=200, w=16, h=16):
    return Portal(
        x=x, y=y, width=w, height=h,
        target_map="town_02", target_position=Position(5, 5),
    )


class TestPortalCenter:
    def test_center_with_size(self):
        p = _portal(x=100, y=200, w=16, h=16)
        assert p.center_x == 108
        assert p.center_y == 208

    def test_center_point_object(self):
        p = _portal(x=100, y=200, w=0, h=0)
        assert p.center_x == 100
        assert p.center_y == 200


class TestIsTriggered:
    def test_full_overlap_triggers(self):
        p = _portal(x=100, y=200, w=16, h=16)
        assert p.is_triggered_by(100, 200, 16, 16)

    def test_partial_overlap_triggers(self):
        p = _portal(x=100, y=200, w=16, h=16)
        # collision rect overlaps portal's right edge
        assert p.is_triggered_by(110, 205, 16, 16)

    def test_edge_touch_triggers(self):
        p = _portal(x=100, y=200, w=16, h=16)
        # collision rect's right edge touches portal's left edge
        assert p.is_triggered_by(84, 200, 16, 16)

    def test_no_overlap_does_not_trigger(self):
        p = _portal(x=100, y=200, w=16, h=16)
        assert not p.is_triggered_by(200, 400, 16, 16)

    def test_one_pixel_gap_does_not_trigger(self):
        p = _portal(x=100, y=200, w=16, h=16)
        # collision rect sits one pixel to the left of portal
        assert not p.is_triggered_by(83, 200, 16, 16)

    def test_point_portal_inside_collision_rect_triggers(self):
        p = _portal(x=50, y=50, w=0, h=0)
        assert p.is_triggered_by(40, 40, 16, 16)

    def test_point_portal_outside_collision_rect_does_not_trigger(self):
        p = _portal(x=100, y=100, w=0, h=0)
        assert not p.is_triggered_by(40, 40, 16, 16)
