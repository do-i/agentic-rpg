# engine/audio/bgm_manager.py
#
# Background music manager — thin wrapper around pygame.mixer.music.
# Tracks the current track to avoid restarting the same song on scene re-entry.
# Loads bgm_index.yaml to resolve logical keys (e.g. "battle.normal") to paths.

from __future__ import annotations

from pathlib import Path

import pygame
import yaml

SOUND_VOLUME = 0.3


class BgmManager:
    """Manages background music playback."""

    def __init__(self, scenario_path: Path | None = None) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self._current: str = ""
        self._index: dict[str, Path] = {}
        pygame.mixer.music.set_volume(SOUND_VOLUME)
        if scenario_path:
            self._load_index(scenario_path)

    def _load_index(self, scenario_path: Path) -> None:
        index_path = scenario_path / "data" / "audio" / "bgm_index.yaml"
        if not index_path.exists():
            return
        with open(index_path) as f:
            data: dict = yaml.safe_load(f) or {}
        audio_root = scenario_path / "assets" / "audio"
        for category, entries in data.items():
            if not isinstance(entries, dict):
                continue
            for key, rel_path in entries.items():
                self._index[f"{category}.{key}"] = audio_root / rel_path

    def play(self, path: str | Path, loops: int = -1, fade_ms: int = 1000) -> None:
        """Start playing *path* if it isn't already playing."""
        resolved = str(path)
        if resolved == self._current:
            return
        self._current = resolved
        pygame.mixer.music.load(resolved)
        pygame.mixer.music.play(loops, fade_ms=fade_ms)

    def play_key(self, key: str, loops: int = -1, fade_ms: int = 1000) -> None:
        """Resolve a logical key from bgm_index.yaml and play it."""
        path = self._index.get(key)
        if path and path.exists():
            self.play(path, loops=loops, fade_ms=fade_ms)

    def stop(self, fade_ms: int = 500) -> None:
        """Fade out and stop."""
        self._current = ""
        pygame.mixer.music.fadeout(fade_ms)

    @property
    def current(self) -> str:
        return self._current
