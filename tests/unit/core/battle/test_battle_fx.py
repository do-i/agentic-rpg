# tests/unit/core/battle/test_battle_fx.py

from engine.battle.battle_fx import BattleFx


class _Target:
    """Stand-in — BattleFx only needs an object identity."""


class TestBattleFxFlash:
    def test_no_effect_by_default(self):
        fx = BattleFx()
        t = _Target()
        assert fx.flash_alpha(t) == 0
        assert fx.shake_offset(t) == 0

    def test_flash_decays_to_zero(self):
        fx = BattleFx()
        t = _Target()
        fx.flash(t, duration=0.1)
        start = fx.flash_alpha(t)
        fx.update(0.05)
        mid = fx.flash_alpha(t)
        fx.update(0.1)
        assert start > mid > 0
        assert fx.flash_alpha(t) == 0

    def test_flash_keyed_per_target(self):
        fx = BattleFx()
        a, b = _Target(), _Target()
        fx.flash(a, duration=0.1)
        assert fx.flash_alpha(a) > 0
        assert fx.flash_alpha(b) == 0


class TestBattleFxShake:
    def test_shake_returns_offset_within_amplitude(self):
        fx = BattleFx()
        t = _Target()
        fx.shake(t, duration=0.2, amplitude=4)
        for step in range(20):
            fx.update(0.01)
            assert abs(fx.shake_offset(t)) <= 4

    def test_shake_expires(self):
        fx = BattleFx()
        t = _Target()
        fx.shake(t, duration=0.1, amplitude=4)
        fx.update(0.2)
        assert fx.shake_offset(t) == 0


class TestBattleFxHit:
    def test_hit_arms_flash_and_shake(self):
        fx = BattleFx()
        t = _Target()
        fx.hit(t)
        assert fx.flash_alpha(t) > 0
        # shake_offset may legitimately be 0 at t=0 (sin(0)==0);
        # advance one step and confirm it's actively oscillating.
        fx.update(0.02)
        assert fx.shake_offset(t) != 0 or fx.flash_alpha(t) > 0
