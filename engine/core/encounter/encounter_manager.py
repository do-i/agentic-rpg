# engine/core/encounter/encounter_manager.py
#
# Phase 4 — Battle system

from __future__ import annotations
import random
from pathlib import Path

from engine.core.encounter.encounter_zone import EncounterZone, load_encounter_zone
from engine.core.encounter.encounter_resolver import EncounterResolver
from engine.core.battle.battle_state import BattleState
from engine.core.battle.combatant import Combatant
from engine.core.state.flag_state import FlagState
from engine.core.state.party_state import PartyState


# Rogue passive base encounter reduction (docs/01-Party.md)
ROGUE_BASE_REDUCTION = -0.15


class EncounterManager:
    """
    Called by WorldMapScene every time the player moves one tile.
    Owns:
      - zone loading and caching
      - step-based encounter roll
      - modifier computation (Rogue passive + accessories)
      - BattleState construction (party side filled here)
      - boss trigger check

    Usage:
        manager.set_zone("zone_01_starting_forest")
        result = manager.on_step(flags, party, inventory_ids)
        if result:
            # launch BattleScene with result
    """

    def __init__(
        self,
        resolver: EncounterResolver,
        encount_dir: Path,
    ) -> None:
        self._resolver = resolver
        self._encount_dir = encount_dir
        self._zone: EncounterZone | None = None
        self._zone_id: str = ""
        self._zone_cache: dict[str, EncounterZone] = {}

    # ── Zone management ───────────────────────────────────────

    def set_zone(self, zone_id: str) -> None:
        """Switch active encounter zone. Called on map transition."""
        if zone_id == self._zone_id:
            return
        self._zone_id = zone_id
        if zone_id in self._zone_cache:
            self._zone = self._zone_cache[zone_id]
            return
        path = self._encount_dir / f"{zone_id}.yaml"
        if path.exists():
            zone = load_encounter_zone(path)
            self._zone_cache[zone_id] = zone
            self._zone = zone
        else:
            self._zone = None   # no encounters in this zone (towns, etc.)

    # ── Step trigger ──────────────────────────────────────────

    def on_step(
        self,
        flags: FlagState,
        party: PartyState,
        inventory_item_ids: set[str],
    ) -> BattleState | None:
        """
        Called once per player tile step on the world map / dungeon.
        Returns BattleState if encounter fires, None otherwise.
        Boss encounters take priority over random encounters.
        """
        if self._zone is None:
            return None

        modifier = self._compute_modifier(party)

        # boss check first
        boss_state = self._resolver.try_boss_encounter(self._zone, flags)
        if boss_state:
            return self._fill_party(boss_state, party)

        # random encounter
        state = self._resolver.try_random_encounter(
            self._zone, modifier, flags, inventory_item_ids
        )
        if state:
            return self._fill_party(state, party)

        return None

    # ── Modifier computation ──────────────────────────────────

    def _compute_modifier(self, party: PartyState) -> float:
        """
        Encounter modifier from Rogue passive + equipped accessories.
        Rogue must be in party for any modifier to apply.
        """
        has_rogue = any(m.class_name.lower() == "rogue" for m in party.members)
        if not has_rogue:
            return 0.0

        modifier = ROGUE_BASE_REDUCTION

        # accessory modifiers from equipped items — stub: Phase 6 reads real equipment
        for member in party.members:
            if member.class_name.lower() != "rogue":
                continue
            acc = member.equipped.get("accessory", "")
            if acc == "stealth_cloak":
                modifier += -0.15
            elif acc == "lure_charm":
                modifier += 0.20

        return modifier

    # ── Party fill ────────────────────────────────────────────

    def _fill_party(self, state: BattleState, party: PartyState) -> BattleState:
        """
        Populate the party side of BattleState from PartyState.
        Full stat loading from character YAML in Phase 5.
        Stub: builds minimal Combatants from MemberState fields.
        """
        state.party = [self._member_to_combatant(m) for m in party.members]
        state.build_turn_order()
        return state

    def _member_to_combatant(self, member) -> Combatant:
        """
        Stub — maps MemberState → Combatant.
        Full equipment stat resolution in Phase 5.
        """
        portrait = f"assets/images/{member.id}_profile.png"
        return Combatant(
            id=member.id,
            name=member.name,
            hp=member.hp,
            hp_max=member.hp_max,
            mp=member.mp,
            mp_max=member.mp_max,
            atk=getattr(member, "str_", 10),
            def_=getattr(member, "con",  8),
            mres=getattr(member, "int_", 6),
            dex=getattr(member, "dex",  10),
            is_enemy=False,
            portrait_path=portrait,
            abilities=[]   # stub — Phase 5 loads from class YAML
        )
