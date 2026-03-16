# engine/core/game.py

import pygame
from engine.core.display import Display
from engine.core.frame_clock import FrameClock


class Game:
    def __init__(self, display: Display, clock: FrameClock) -> None:
        self._display = display
        self._clock = clock
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            self._clock.tick()
            self._handle_events()
            self._update()
            self._render()
            self._display.flip()
        self._display.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False

    def _update(self) -> None:
        pass

    def _render(self) -> None:
        self._display.screen.fill((0, 0, 0))