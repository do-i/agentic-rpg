# engine/core/game.py

import pygame
from engine.core.display import Display
from engine.core.frame_clock import FrameClock
from engine.core.scene_manager import SceneManager


class Game:
    def __init__(self, display: Display, clock: FrameClock, scene_manager: SceneManager) -> None:
        self._display = display
        self._clock = clock
        self._scene_manager = scene_manager
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            self._clock.tick()
            events = pygame.event.get()
            self._handle_events(events)
            self._scene_manager.update(self._clock.delta)
            self._scene_manager.render(self._display.screen)
            self._display.flip()
        self._display.quit()

    def _handle_events(self, events: list) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self._running = False
        self._scene_manager.handle_events(events)