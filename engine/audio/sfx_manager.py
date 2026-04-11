# engine/audio/sfx_manager.py
#
# Sound effects manager — thin wrapper around pygame.mixer.Sound.
# Loads a scenario-level sfx_index.yaml and plays sounds by logical event key.

from __future__ import annotations

from pathlib import Path

import pygame
import yaml

SFX_VOLUME = 0.8


class SfxManager:
    """Manages battle and UI sound effect playback."""

    def __init__(self, scenario_path: Path) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._load(scenario_path)

    def _load(self, scenario_path: Path) -> None:
        sfx_map_path = scenario_path / "data" / "audio" / "sfx_index.yaml"
        if not sfx_map_path.exists():
            return
        with open(sfx_map_path) as f:
            sfx_map: dict = yaml.safe_load(f) or {}
        audio_root = scenario_path / "assets" / "audio"
        for _category, entries in sfx_map.items():
            if not isinstance(entries, dict):
                continue
            for key, rel_path in entries.items():
                full_path = audio_root / rel_path
                if not full_path.exists():
                    continue
                try:
                    sound = pygame.mixer.Sound(str(full_path))
                    sound.set_volume(SFX_VOLUME)
                    self._sounds[key] = sound
                except Exception as e:
                    print(f"[SFX] failed to load {full_path}: {e}")

    def play(self, key: str) -> None:
        """Play a sound by event key. No-op if key is not in the map."""
        sound = self._sounds.get(key)
        if sound:
            sound.play()

    def play_battle_action(self, action: dict) -> None:
        """Derive the SFX key from a pending_action dict and play it."""
        atype = action.get("type")
        data = action.get("data") or {}

        if atype == "attack":
            self.play("atk_slash")
        elif atype == "defend":
            self.play("defend")
        elif atype == "spell":
            spell_type = data.get("type")
            element = data.get("element")
            if spell_type == "heal":
                self.play("heal")
            elif spell_type == "revive":
                self.play("revive")
            elif spell_type == "buff":
                stat = (data.get("effect") or {}).get("stat", "")
                self.play("def_buff" if stat == "def_" else "atk_buff")
            elif spell_type == "debuff":
                self.play("debuff")
            elif spell_type == "utility":
                self.play("heal")
            elif element:
                self.play(f"spell_{element}")
        elif atype == "item":
            self.play("use_item")
