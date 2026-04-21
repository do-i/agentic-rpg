# engine/util/frame_clock.py

import pygame

# Clock as written is frame timing only — keeps the game loop running at 60 FPS and provides delta for smooth movement/animation. That's its single responsibility.
# Time-based game mechanics — status effect duration, poison tick, tent/inn recovery — need a separate concept:
# GameClock — tracks in-game time, independent of frame rate.
class FrameClock:
    def __init__(self, fps: int) -> None:
        self._fps = fps
        self._clock = pygame.time.Clock()
        self._delta: float = 0.0

    @property
    def delta(self) -> float:
        """Time in seconds since last tick."""
        return self._delta

    def tick(self) -> None:
        self._delta = self._clock.tick(self._fps) / 1000.0