# tests/unit/world/test_portal.py

from engine.world.portal import Portal, PORTAL_TRIGGER_RADIUS
from engine.core.models.position import Position


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
    def test_exact_overlap_triggers(self):
        p = _portal(x=100, y=200, w=16, h=16)
        # collision rect centered on portal center (108, 208)
        assert p.is_triggered_by(100, 200, 16, 16)

    def test_within_radius_triggers(self):
        p = _portal(x=100, y=200, w=16, h=16)
        # shift collision rect slightly — still within radius
        assert p.is_triggered_by(100 + PORTAL_TRIGGER_RADIUS - 1, 200, 16, 16)

    def test_outside_radius_does_not_trigger(self):
        p = _portal(x=100, y=200, w=16, h=16)
        # shift far away
        assert not p.is_triggered_by(200, 400, 16, 16)

    def test_just_at_boundary(self):
        p = _portal(x=0, y=0, w=0, h=0)
        # col center at (PORTAL_TRIGGER_RADIUS, 0) — dx == radius, should trigger
        assert p.is_triggered_by(PORTAL_TRIGGER_RADIUS, 0, 0, 0)

    def test_just_outside_boundary(self):
        p = _portal(x=0, y=0, w=0, h=0)
        assert not p.is_triggered_by(PORTAL_TRIGGER_RADIUS + 1, 0, 0, 0)
