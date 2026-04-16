# engine/game.py

import pygame
from engine.settings.engine_config_data import EngineConfigData
from engine.util.frame_clock import FrameClock
from engine.common.scene.scene_manager import SceneManager
from engine.record.recorder import RecordPlaybackManager

_REPEAT_KEYS     = {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}
_REPEAT_DELAY    = 0.25   # seconds before first repeat fires
_REPEAT_INTERVAL = 0.07   # seconds between subsequent repeats


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
        self._held: dict[int, float] = {}  # key → seconds until next synthetic KEYDOWN

    def run(self) -> None:
        self._running = True
        steps = max(1, round(self._playback_speed))
        while self._running:
            self._clock.tick()
            for _ in range(steps):
                events = self._recorder.get_events(self._clock.delta)
                self._handle_events(events)
                synthetic = self._tick_key_repeat(self._clock.delta)
                if synthetic:
                    self._scene_manager.handle_events(synthetic)
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
            elif event.type == pygame.KEYDOWN and event.key in _REPEAT_KEYS:
                self._held[event.key] = _REPEAT_DELAY
            elif event.type == pygame.KEYUP and event.key in _REPEAT_KEYS:
                self._held.pop(event.key, None)
        self._scene_manager.handle_events(events)

    def _tick_key_repeat(self, delta: float) -> list[pygame.event.Event]:
        synthetic = []
        for key in list(self._held):
            self._held[key] -= delta
            if self._held[key] <= 0:
                synthetic.append(
                    pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode='', scancode=0)
                )
                self._held[key] += _REPEAT_INTERVAL
        return synthetic
