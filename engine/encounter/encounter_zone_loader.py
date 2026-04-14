# engine/io/encounter_zone_loader.py

from __future__ import annotations
from pathlib import Path
import yaml

from engine.encounter.encounter_zone_data import (
    Formation,
    EncounterSet,
    BossConfig,
    BarrierEnemy,
    EncounterZone,
)


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
                chase_range=int(entry.get("chase_range", 0)),
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

    raw_freq = data.get("spawn_frequency")
    spawn_frequency = float(raw_freq) if raw_freq is not None else None

    return EncounterZone(
        zone_id=data.get("id", path.stem),
        name=data.get("name", ""),
        density=float(data.get("density", data.get("encounter_rate", 0.5))),
        set_a=parse_set(data.get("set_a")),
        set_b=parse_set(data.get("set_b")),
        boss=boss,
        barrier_enemies=barriers,
        background=data.get("background", ""),
        spawn_frequency=spawn_frequency,
    )
