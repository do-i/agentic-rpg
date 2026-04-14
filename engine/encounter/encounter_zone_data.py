# engine/dto/encounter_zone.py

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Formation:
    enemy_ids:   list[str]
    weight:      int
    chase_range: int = 0


@dataclass(frozen=True)
class EncounterSet:
    entries: list[Formation] = field(default_factory=list)

    @property
    def total_weight(self) -> int:
        return sum(e.weight for e in self.entries)


@dataclass(frozen=True)
class BossConfig:
    enemy_id:    str
    name:        str
    once:        bool = True
    flag_set:    str  = ""   # set_flag on_complete


@dataclass(frozen=True)
class BarrierEnemy:
    enemy_id:        str
    requires_item:   str
    blocked_message: str = "A mysterious force blocks your attack."


@dataclass(frozen=True)
class EncounterZone:
    """
    Parsed encounter zone — loaded from data/encount/<zone_id>.yaml.
    Contains set_a, set_b, boss config, barrier enemy list, density, and spawn frequency.
    """
    zone_id:         str
    name:            str
    density:         float          # 0-1 probability a spawn tick fires
    set_a:           EncounterSet
    set_b:           EncounterSet
    boss:            BossConfig | None = None
    barrier_enemies: list[BarrierEnemy] = field(default_factory=list)
    background:      str = ""
    spawn_frequency: float | None = None  # optional zone-level interval override (seconds)
