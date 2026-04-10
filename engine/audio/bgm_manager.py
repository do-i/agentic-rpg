# engine/audio/bgm_manager.py
#
# Background music manager — thin wrapper around pygame.mixer.music.
# Tracks the current track to avoid restarting the same song on scene re-entry.

from __future__ import annotations

from pathlib import Path

import pygame

SOUND_VOLUME = 0.3
class BgmManager:
    """Manages background music playback."""

    def __init__(self) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self._current: str = ""
        pygame.mixer.music.set_volume(SOUND_VOLUME)

    def play(self, path: str | Path, loops: int = -1, fade_ms: int = 1000) -> None:
        """Start playing *path* if it isn't already playing."""
        resolved = str(path)
        if resolved == self._current:
            return
        self._current = resolved
        pygame.mixer.music.load(resolved)
        pygame.mixer.music.play(loops, fade_ms=fade_ms)

    def stop(self, fade_ms: int = 500) -> None:
        """Fade out and stop."""
        self._current = ""
        pygame.mixer.music.fadeout(fade_ms)

    @property
    def current(self) -> str:
        return self._current
