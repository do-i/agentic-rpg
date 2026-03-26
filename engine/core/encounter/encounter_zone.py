# engine/core/encounter/encounter_zone.py
#
# Phase 4 — Battle system

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Formation:
    enemy_ids: list[str]
    weight:    int


@dataclass
class EncounterSet:
    entries: list[Formation] = field(default_factory=list)

    @property
    def total_weight(self) -> int:
        return sum(e.weight for e in self.entries)


@dataclass
class BossConfig:
    enemy_id:    str
    name:        str
    once:        bool = True
    flag_set:    str  = ""   # set_flag on_complete


@dataclass
class BarrierEnemy:
    enemy_id:        str
    requires_item:   str
    blocked_message: str = "A mysterious force blocks your attack."


@dataclass
class EncounterZone:
    """
    Parsed encounter zone — loaded from data/encount/<zone_id>.yaml.
    Contains set_a, set_b, boss config, barrier enemy list, and base rate.
    """
    zone_id:        str
    name:           str
    encounter_rate: float
    set_a:          EncounterSet
    set_b:          EncounterSet
    boss:           BossConfig | None = None
    barrier_enemies: list[BarrierEnemy] = field(default_factory=list)


def load_encounter_zone(path: Path) -> EncounterZone:
    """Parse a single encount YAML file into an EncounterZone."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    def parse_set(raw: dict | None) -> EncounterSet:
        if not raw:
            return EncounterSet()
        entries = [
            Formation(
                enemy_ids=entry["formation"],
                weight=entry["weight"],
            )
            for entry in raw.get("entries", [])
        ]
        return EncounterSet(entries=entries)

    boss = None
    raw_boss = data.get("boss")
    if raw_boss:
        on_complete = raw_boss.get("on_complete", {}) or {}
        boss = BossConfig(
            enemy_id=raw_boss["id"],
            name=raw_boss.get("name", raw_boss["id"]),
            once=raw_boss.get("once", True),
            flag_set=on_complete.get("set_flag", ""),
        )

    barriers = [
        BarrierEnemy(
            enemy_id=b["id"],
            requires_item=b.get("requires_item", ""),
            blocked_message=b.get("blocked_message", "A mysterious force blocks your attack."),
        )
        for b in data.get("barrier_enemies", [])
    ]

    return EncounterZone(
        zone_id=data.get("id", path.stem),
        name=data.get("name", ""),
        encounter_rate=float(data.get("encounter_rate", 0.0)),
        set_a=parse_set(data.get("set_a")),
        set_b=parse_set(data.get("set_b")),
        boss=boss,
        barrier_enemies=barriers,
    )
