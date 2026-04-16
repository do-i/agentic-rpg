import pickle
import pygame.locals as _pg_locals
from collections import defaultdict
from pathlib import Path

import pygame

from engine.record.record_format import RecordedSession, RecordedFrame, RECORDING_VERSION

# All K_* constants from pygame.locals, evaluated once at import time.
# Using these as dict keys ensures get_key_state()[pygame.K_UP] works correctly
# regardless of how SDL2 maps scancodes internally.
_KEY_CONSTANTS: list[int] = [
    v for k, v in vars(_pg_locals).items()
    if k.startswith("K_") and isinstance(v, int)
]


def _serialize_keys() -> dict:
    """Return a sparse dict of {K_constant: 1} for every pressed key."""
    pressed = pygame.key.get_pressed()
    return {k: 1 for k in _KEY_CONSTANTS if pressed[k]}


class RecordPlaybackManager:
    def __init__(self, mode: str, recording_file: str, playback_speed: float = 1.0) -> None:
        self._mode = mode
        self._recording_file = Path(recording_file)
        self._speed = max(playback_speed, 0.0)
        self._frame_index = 0
        self._current_key_state: dict | None = None
        self._session: RecordedSession

        if mode == "playback":
            with open(self._recording_file, "rb") as f:
                self._session = pickle.load(f)
            if self._session.version != RECORDING_VERSION:
                raise ValueError(
                    f"Recording version mismatch: expected {RECORDING_VERSION}, "
                    f"got {self._session.version}"
                )
        else:
            self._session = RecordedSession()

    def get_events(self) -> list:
        """Drop-in replacement for pygame.event.get()."""
        if self._mode == "normal":
            return pygame.event.get()

        if self._mode == "record":
            events = pygame.event.get()
            serialized = [{"type": e.type, "dict": e.dict} for e in events]
            self._session.frames.append(
                RecordedFrame(
                    frame_index=self._frame_index,
                    events=serialized,
                    key_state=_serialize_keys(),
                )
            )
            self._frame_index += 1
            return events

        # playback — consume multiple frames per tick when speed > 1
        frames_to_consume = max(1, round(self._speed))
        merged_events: list = []
        for _ in range(frames_to_consume):
            if self._frame_index >= len(self._session.frames):
                return [pygame.event.Event(pygame.QUIT)]
            frame = self._session.frames[self._frame_index]
            merged_events += [pygame.event.Event(e["type"], e["dict"]) for e in frame.events]
            self._current_key_state = frame.key_state
            self._frame_index += 1
        return merged_events

    def get_key_state(self):
        """Drop-in replacement for pygame.key.get_pressed(). Returns a defaultdict(int)."""
        if self._mode == "playback":
            source = self._current_key_state or {}
            return defaultdict(int, source)
        return pygame.key.get_pressed()

    def set_seed(self, seed: int) -> None:
        """Store the RNG seed in the session. Call before any frames are recorded."""
        if self._mode != "playback":
            self._session.seed = seed

    @property
    def session_seed(self) -> int:
        return self._session.seed

    def save(self) -> None:
        """Pickle session to disk. No-op in normal/playback modes."""
        if self._mode != "record":
            return
        with open(self._recording_file, "wb") as f:
            pickle.dump(self._session, f)
