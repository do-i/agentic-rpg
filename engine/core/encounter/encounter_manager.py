# engine/core/encounter/encounter_manager.py
#
# Phase 4 — Battle system
# Phase 6 — magic_core tag added to MC drops

from __future__ import annotations
from pathlib import Path

from engine.core.encounter.encounter_zone import EncounterZone, load_encounter_zone
from engine.core.encounter.encounter_resolver import EncounterResolver
from engine.core.battle.battle_state import BattleState
from engine.core.battle.combatant import Combatant
from engine.core.state.flag_state import FlagState
from engine.core.state.party_state import PartyState, MemberState
from engine.core.state.repository_state import RepositoryState

ROGUE_BASE_REDUCTION = -0.05

# MC item ids that get the magic_core tag
MC_ITEM_IDS = {"mc_xs", "mc_s", "mc_m", "mc_l", "mc_xl"}


def _add_mc(repository: RepositoryState, item_id: str, qty: int) -> None:
    """Add a Magic Core item and ensure it carries the magic_core tag."""
    repository.add_item(item_id, qty)
    entry = repository.get_item(item_id)
    if entry is not None:
        entry.tags.add("magic_core")


class EncounterManager:
    """
    Called by WorldMapScene every tile step.
    Owns zone loading, encounter roll, modifier computation,
    BattleState construction, and boss trigger check.
    """

    def __init__(
        self,
        resolver: EncounterResolver,
        encount_dir: Path,
    ) -> None:
        self._resolver    = resolver
        self._encount_dir = encount_dir
        self._zone: EncounterZone | None = None
        self._zone_id: str = ""
        self._zone_cache: dict[str, EncounterZone] = {}

    # ── Zone management ───────────────────────────────────────

    def set_zone(self, zone_id: str) -> None:
        if zone_id == self._zone_id and self._zone is not None:
            return
        path = self._encount_dir / f"{zone_id}.yaml"
        if path.exists():
            self._zone_id = zone_id
            if zone_id not in self._zone_cache:
                self._zone_cache[zone_id] = load_encounter_zone(path)
            self._zone = self._zone_cache[zone_id]
        else:
            self._zone = None  # towns, inns — encounters disabled

    # ── Step trigger ──────────────────────────────────────────

    def on_step(
        self,
        flags: FlagState,
        party: PartyState,
        inventory_item_ids: set[str],
    ) -> BattleState | None:
        if self._zone is None:
            return None

        modifier = self._compute_modifier(party)

        boss_state = self._resolver.try_boss_encounter(self._zone, flags)
        if boss_state:
            return self._fill_party(boss_state, party)

        state = self._resolver.try_random_encounter(
            self._zone, modifier, flags, inventory_item_ids
        )
        if state:
            return self._fill_party(state, party)

        return None

    # ── Post-battle MC tagging ────────────────────────────────

    @staticmethod
    def add_mc_drops(repository: RepositoryState, mc_drops: list[dict]) -> None:
        """
        Called by BattleScene after victory to add MC drops to the repository.
        Ensures magic_core tag is set on every MC item.
        size keys: XS, S, M, L, XL (uppercase from reward calc).
        """
        for mc in mc_drops:
            size   = mc.get("size", "S").lower()
            qty    = mc.get("qty", 1)
            item_id = f"mc_{size}"
            _add_mc(repository, item_id, qty)

    # ── Modifier ──────────────────────────────────────────────

    def _compute_modifier(self, party: PartyState) -> float:
        has_rogue = any(m.class_name.lower() == "rogue" for m in party.members)
        if not has_rogue:
            return 0.0
        modifier = ROGUE_BASE_REDUCTION
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
        state.party = [self._member_to_combatant(m) for m in party.members]
        state.build_turn_order()
        return state

    def _member_to_combatant(self, member: MemberState) -> Combatant:
        return Combatant(
            id=member.id,
            name=member.name,
            hp=member.hp,
            hp_max=member.hp_max,
            mp=member.mp,
            mp_max=member.mp_max,
            atk=member.str_,
            def_=member.con,
            mres=member.int_,
            dex=member.dex,
            is_enemy=False,
            portrait_path=f"assets/images/{member.id}_profile.png",
            abilities=[],
        )
