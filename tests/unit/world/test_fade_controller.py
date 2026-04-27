# tests/unit/world/test_fade_controller.py

from engine.world.fade_controller import FADE_SPEED, FadeController


class TestInitialState:
    def test_starts_fully_black_fading_in(self):
        fc = FadeController()
        assert fc.alpha == 255
        assert fc.is_fading_in
        assert not fc.is_idle
        assert not fc.is_fading_out

    def test_blocks_input_during_initial_fade_in(self):
        fc = FadeController()
        assert fc.blocks_input is True


class TestFadeIn:
    def test_alpha_decreases_each_update(self):
        fc = FadeController()
        fc.update(0.1)
        assert fc.alpha < 255

    def test_completes_to_idle_at_zero(self):
        fc = FadeController()
        # Drive past completion in one big step (FADE_SPEED * 1.0 == 300 > 255).
        result = fc.update(1.0)
        assert result is None
        assert fc.alpha == 0
        assert fc.is_idle

    def test_idle_after_fade_in_does_not_block_input(self):
        fc = FadeController()
        fc.update(1.0)
        assert fc.blocks_input is False


class TestFadeOut:
    def test_start_fade_out_queues_transition_and_flips_direction(self):
        fc = FadeController()
        fc.update(1.0)  # finish fade-in -> idle
        transition = {"map": "town_02"}

        fc.start_fade_out(transition)

        assert fc.is_fading_out
        assert fc.alpha == 0
        assert fc.blocks_input is True

    def test_alpha_increases_each_update(self):
        fc = FadeController()
        fc.update(1.0)
        fc.start_fade_out({"map": "x"})
        fc.update(0.1)
        assert fc.alpha > 0
        assert fc.alpha < 255

    def test_completes_returns_transition_once(self):
        fc = FadeController()
        fc.update(1.0)
        transition = {"map": "town_02"}
        fc.start_fade_out(transition)

        # One step large enough to land at 255.
        seconds = 256 / FADE_SPEED
        result = fc.update(seconds)
        assert result is transition
        assert fc.alpha == 255
        assert fc.is_idle

        # Subsequent calls return None (transition was consumed).
        assert fc.update(0.1) is None

    def test_start_fade_out_ignored_while_already_fading_out(self):
        fc = FadeController()
        fc.update(1.0)
        first = {"map": "first"}
        second = {"map": "second"}
        fc.start_fade_out(first)
        fc.update(0.05)
        mid_alpha = fc.alpha

        fc.start_fade_out(second)

        # State preserved: still fading the first transition; alpha not reset.
        assert fc.is_fading_out
        assert fc.alpha == mid_alpha
        # Drive to completion and confirm we get `first`, not `second`.
        result = fc.update(1.0)
        assert result is first


class TestReset:
    def test_returns_to_initial_fade_in_state(self):
        fc = FadeController()
        fc.update(1.0)
        fc.start_fade_out({"map": "x"})
        fc.update(0.05)

        fc.reset()

        assert fc.alpha == 255
        assert fc.is_fading_in
        assert not fc.is_fading_out

    def test_drops_pending_transition(self):
        fc = FadeController()
        fc.update(1.0)
        fc.start_fade_out({"map": "x"})
        fc.reset()
        # After reset, fading-in to completion should not surface a transition.
        result = fc.update(1.0)
        assert result is None
