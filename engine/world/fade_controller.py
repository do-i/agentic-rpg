# engine/world/fade_controller.py
#
# Fade-to-black state machine used by the world map for portal transitions.
#
# States: -1 fading in, 0 idle, 1 fading out (with a pending transition).
from __future__ import annotations


FADE_SPEED = 300


class FadeController:
    """Owns fade alpha + direction + the transition queued behind a fade-out."""

    def __init__(self) -> None:
        self._alpha: int = 255
        self._dir: int = -1
        self._pending: dict | None = None

    @property
    def alpha(self) -> int:
        return self._alpha

    @property
    def is_idle(self) -> bool:
        return self._dir == 0

    @property
    def is_fading_in(self) -> bool:
        return self._dir == -1

    @property
    def is_fading_out(self) -> bool:
        return self._dir == 1

    @property
    def blocks_input(self) -> bool:
        # Block player input during the opening fade-in (until alpha hits 0)
        # and the entire fade-out (the player has already triggered a portal).
        if self._dir == 1:
            return True
        if self._dir == -1 and self._alpha > 0:
            return True
        return False

    def reset(self) -> None:
        """Restart at fully-black, fading in. Used on map transitions and new-game."""
        self._alpha = 255
        self._dir = -1
        self._pending = None

    def start_fade_out(self, transition: dict) -> None:
        """Begin a fade-out toward `transition`. Ignored if already fading out."""
        if self._dir == 1:
            return
        self._pending = transition
        self._dir = 1
        self._alpha = 0

    def update(self, delta: float) -> dict | None:
        """Advance the fade.

        Returns the pending transition exactly once — the frame the fade-out
        completes. The caller is responsible for applying it; subsequent calls
        return None until `start_fade_out` is called again.
        """
        if self._dir == 0:
            return None
        self._alpha += int(FADE_SPEED * delta) * self._dir
        if self._dir == 1 and self._alpha >= 255:
            self._alpha = 255
            self._dir = 0
            transition = self._pending
            self._pending = None
            return transition
        if self._dir == -1 and self._alpha <= 0:
            self._alpha = 0
            self._dir = 0
        return None
