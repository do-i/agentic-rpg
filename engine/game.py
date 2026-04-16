# engine/game.py

import pygame
from engine.settings.engine_config_data import EngineConfigData
from engine.util.frame_clock import FrameClock
from engine.common.scene.scene_manager import SceneManager
from engine.record.recorder import RecordPlaybackManager


class Game:
    def __init__(
        self,
        config: EngineConfigData,
        clock: FrameClock,
        scene_manager: SceneManager,
        recorder: RecordPlaybackManager,
        playback_speed: float = 1.0,
    ) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode(
            (config.screen_width, config.screen_height),
            pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption(config.window_title)
        self._clock = clock
        self._scene_manager = scene_manager
        self._recorder = recorder
        self._playback_speed = playback_speed
        self._running = False

    def run(self) -> None:
        self._running = True
        steps = max(1, round(self._playback_speed))
        while self._running:
            self._clock.tick()
            for _ in range(steps):
                events = self._recorder.get_events(self._clock.delta)
                self._handle_events(events)
                delta = self._recorder.replay_delta or self._clock.delta
                self._scene_manager.update(delta)
                if not self._running:
                    break
            self._scene_manager.render(self._screen)
            pygame.display.flip()
        pygame.quit()

    def _handle_events(self, events: list) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self._recorder.save()
                self._running = False
        self._scene_manager.handle_events(events)