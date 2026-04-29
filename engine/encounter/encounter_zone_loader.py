# engine/encounter/encounter_zone_loader.py

from __future__ import annotations
from pathlib import Path

from engine.io.yaml_loader import load_yaml_required
from engine.encounter.encounter_zone_data import (
    Formation,
    EncounterSet,
    BossConfig,
    BarrierEnemy,
    EncounterZone,
)


def _require(data: dict, key: str, ctx: str):
    if key not in data:
        raise KeyError(f"{ctx}: missing required field {key!r}")
    return data[key]


def load_encounter_zone(path: Path) -> EncounterZone:
    """Parse a single encount YAML file into an EncounterZone."""
    data = load_yaml_required(path)

    ctx = f"encount file {path.name}"

    entries = [
        Formation(
            enemy_ids=entry["formation"],
            weight=entry["weight"],
            chase_range=int(_require(entry, "chase_range", f"{ctx} entry")),
        )
        for entry in data.get("entries", [])
    ]

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
            blocked_message=_require(b, "blocked_message", f"{ctx} barrier"),
        )
        for b in data.get("barrier_enemies", [])
    ]

    raw_freq = data.get("spawn_frequency")

    return EncounterZone(
        zone_id=data.get("id", path.stem),
        name=data.get("name", ""),
        density=float(_require(data, "density", ctx)),
        entries=EncounterSet(entries=entries),
        boss=boss,
        barrier_enemies=barriers,
        background=data.get("background", ""),
        spawn_frequency=float(raw_freq) if raw_freq is not None else None,
    )
