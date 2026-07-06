# engine/game.py

from __future__ import annotations

import os
import pygame
from engine.settings.engine_config_data import EngineConfigData
from engine.util.frame_clock import FrameClock
from engine.common.scene.scene_manager import SceneManager
from engine.common.ui.framebuffer import ensure_framebuffer, present_frame
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
        window_title: str,
        playback_speed: float = 1.0,
    ) -> None:
        self._apply_window_position(config.window_position)
        pygame.init()
        self._screen = pygame.display.set_mode(
            (config.screen_width, config.screen_height),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption(window_title)
        self._framebuffer: pygame.Surface | None = None
        self._clock = clock
        self._scene_manager = scene_manager
        self._recorder = recorder
        self._playback_speed = max(playback_speed, 0.01)
        self._playback_accumulator = 0.0
        self._running = False
        self._held: dict[int, float] = {}  # key → seconds until next synthetic KEYDOWN

    @staticmethod
    def _apply_window_position(value: str) -> None:
        if value == "center":
            os.environ["SDL_VIDEO_CENTERED"] = "1"
            return
        parts = value.split(",")
        if len(parts) != 2 or not all(p.strip().lstrip("-").isdigit() for p in parts):
            raise ValueError(
                f"Invalid display.window_position {value!r} in settings.yaml: "
                f'expected "center" or "X,Y" (e.g. "100,50")'
            )
        x, y = (int(p.strip()) for p in parts)
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"

    def run(self) -> None:
        self._running = True
        while self._running:
            self._clock.tick()
            for _ in range(self._playback_steps_this_frame()):
                events = self._recorder.get_events(self._clock.delta)
                self._handle_events(events)
                synthetic = self._tick_key_repeat(self._clock.delta)
                if synthetic:
                    self._scene_manager.handle_events(synthetic)
                delta = self._recorder.replay_delta or self._clock.delta
                self._scene_manager.update(delta)
                if not self._running:
                    break
            self._framebuffer = ensure_framebuffer(self._framebuffer, self._screen.get_size())
            self._scene_manager.render(self._framebuffer)
            present_frame(self._screen, self._framebuffer)
            pygame.display.flip()
        pygame.quit()

    def _playback_steps_this_frame(self) -> int:
        self._playback_accumulator += self._playback_speed
        steps = int(self._playback_accumulator)
        if steps > 0:
            self._playback_accumulator -= steps
        return steps

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
