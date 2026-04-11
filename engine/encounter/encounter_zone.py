# engine/encounter/encounter_zone.py
#
# Re-exports for backwards compatibility.
# DTOs live in engine.common.encounter_zone_data, loader in engine.encounter.encounter_zone_loader.

from engine.common.encounter_zone_data import (
    Formation,
    EncounterSet,
    BossConfig,
    BarrierEnemy,
    EncounterZone,
)
from engine.encounter.encounter_zone_loader import load_encounter_zone

__all__ = [
    "Formation",
    "EncounterSet",
    "BossConfig",
    "BarrierEnemy",
    "EncounterZone",
    "load_encounter_zone",
]
