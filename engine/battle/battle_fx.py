# engine/battle/battle_fx.py
#
# Per-combatant hit effects — white flash and hurt shake.
# Timers are keyed by the Python object id of each Combatant so multiple
# copies of the same enemy type don't collide.

from __future__ import annotations

import math
from dataclasses import dataclass


FLASH_DURATION   = 0.10
SHAKE_DURATION   = 0.22
SHAKE_AMPLITUDE  = 4
SHAKE_FREQ       = 22.0
FLASH_COLOR      = (255, 255, 255)

# Attack animation: enemy plays a sprite-row animation when acting.
ATTACK_DURATION_SEC = 0.5


@dataclass
class _Flash:
    duration: float
    color:    tuple[int, int, int]
    elapsed:  float = 0.0

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.duration

    def alpha(self) -> int:
        if self.duration <= 0 or self.expired:
            return 0
        remaining = 1.0 - self.elapsed / self.duration
        return max(0, min(255, int(255 * remaining)))


@dataclass
class _Shake:
    duration:  float
    amplitude: int
    elapsed:   float = 0.0

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.duration

    def offset(self) -> int:
        if self.duration <= 0 or self.expired:
            return 0
        decay = max(0.0, 1.0 - self.elapsed / self.duration)
        return int(self.amplitude * decay * math.sin(self.elapsed * SHAKE_FREQ))


@dataclass
class _AttackAnim:
    duration: float
    kind:     str   # "thrust" or "spellcast"
    elapsed:  float = 0.0

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.duration

    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.duration)


class BattleFx:
    """Tracks active hit effects per combatant."""

    def __init__(self) -> None:
        self._flashes: dict[int, _Flash] = {}
        self._shakes:  dict[int, _Shake] = {}
        self._attacks: dict[int, _AttackAnim] = {}

    def flash(self, target, duration: float = FLASH_DURATION,
              color: tuple[int, int, int] = FLASH_COLOR) -> None:
        self._flashes[id(target)] = _Flash(duration=duration, color=color)

    def shake(self, target, duration: float = SHAKE_DURATION,
              amplitude: int = SHAKE_AMPLITUDE) -> None:
        self._shakes[id(target)] = _Shake(duration=duration, amplitude=amplitude)

    def hit(self, target) -> None:
        """White flash + hurt shake — the default 'got hit' combo."""
        self.flash(target)
        self.shake(target)

    def play_attack(self, target, kind: str = "thrust",
                    duration: float = ATTACK_DURATION_SEC) -> None:
        """Start an attack animation on the attacker (kind: 'thrust' or 'spellcast')."""
        self._attacks[id(target)] = _AttackAnim(duration=duration, kind=kind)

    def attack_progress(self, target) -> tuple[str, float] | None:
        """Return (kind, 0..1 progress) if an attack animation is active, else None."""
        fx = self._attacks.get(id(target))
        if fx is None or fx.expired:
            return None
        return (fx.kind, fx.progress())

    def update(self, delta: float) -> None:
        for fx in self._flashes.values():
            fx.elapsed += delta
        for fx in self._shakes.values():
            fx.elapsed += delta
        for fx in self._attacks.values():
            fx.elapsed += delta
        self._flashes = {k: v for k, v in self._flashes.items() if not v.expired}
        self._shakes  = {k: v for k, v in self._shakes.items()  if not v.expired}
        self._attacks = {k: v for k, v in self._attacks.items() if not v.expired}

    def flash_alpha(self, target) -> int:
        fx = self._flashes.get(id(target))
        return fx.alpha() if fx else 0

    def flash_color(self, target) -> tuple[int, int, int]:
        fx = self._flashes.get(id(target))
        return fx.color if fx else FLASH_COLOR

    def shake_offset(self, target) -> int:
        fx = self._shakes.get(id(target))
        return fx.offset() if fx else 0
