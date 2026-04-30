# engine/party/party_stats.py
#
# Party-derived passive stats. These are computed from the active party
# composition (class membership) — distinct from per-member stats and
# from temporary battle statuses.
#
# Authoritative design — see docs/design/party.md "Party-Wide Stats".

from __future__ import annotations

from engine.party.party_state import PartyState

# Rogue passive: reduces random encounter rate by 20%.
ROGUE_ENCOUNTER_REDUCTION = 0.20


def has_rogue(party: PartyState) -> bool:
    return any(m.class_name.lower() == "rogue" for m in party.members)


def encounter_modifier(party: PartyState | None) -> float:
    """Multiplier applied to the random-encounter roll rate.

    1.0 = baseline; <1.0 = fewer encounters. A Rogue in the party reduces
    the rate by ``ROGUE_ENCOUNTER_REDUCTION``.
    """
    if party is None:
        return 1.0
    if has_rogue(party):
        return 1.0 - ROGUE_ENCOUNTER_REDUCTION
    return 1.0


def has_trap_detect(party: PartyState | None) -> bool:
    """True when any party member's class grants chest-trap detection.

    Only the Rogue has ``chest_trap_detect: true`` in the shipped scenario;
    encoding it as a class-membership check (rather than reading the class
    YAML at runtime) keeps the dependency direction simple.
    """
    if party is None:
        return False
    return has_rogue(party)
