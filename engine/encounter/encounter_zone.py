# engine/encounter/encounter_zone.py
#
# Re-exports for backwards compatibility.
# DTOs live in engine.dto.encounter_zone, loader in engine.io.encounter_zone_loader.

from engine.dto.encounter_zone import (
    Formation,
    EncounterSet,
    BossConfig,
    BarrierEnemy,
    EncounterZone,
)
from engine.io.encounter_zone_loader import load_encounter_zone

__all__ = [
    "Formation",
    "EncounterSet",
    "BossConfig",
    "BarrierEnemy",
    "EncounterZone",
    "load_encounter_zone",
]
