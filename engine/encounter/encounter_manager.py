# engine/encounter/encounter_manager.py

from __future__ import annotations
from pathlib import Path

import yaml

from engine.encounter.encounter_zone import EncounterZone, load_encounter_zone
from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.party.party_state import PartyState
from engine.party.member_state import MemberState
from engine.party.repository_state import RepositoryState
from engine.item.item_catalog import ItemCatalog
from engine.equipment.equipment_logic import stat_totals

# MC item ids that get the magic_core tag
MC_ITEM_IDS = {"mc_xs", "mc_s", "mc_m", "mc_l", "mc_xl"}


def _add_mc(repository: RepositoryState, item_id: str, qty: int) -> None:
    """Add a Magic Core item and ensure it carries the magic_core tag."""
    entry = repository.add_item(item_id, qty)
    entry.tags.add("magic_core")


class EncounterManager:
    """
    Owns encounter zone loading, party-to-combatant conversion, and MC drop tagging.
    Zone selection and spawn/trigger logic has moved to EnemySpawner.
    """

    def __init__(
        self,
        encount_dir: Path,
        classes_dir: Path | None = None,
        item_catalog: ItemCatalog | None = None,
    ) -> None:
        self._encount_dir = encount_dir
        self._classes_dir = classes_dir
        self._item_catalog = item_catalog
        self._zone: EncounterZone | None = None
        self._zone_id: str = ""
        self._zone_cache: dict[str, EncounterZone] = {}
        self._class_cache: dict[str, list[dict]] = {}

    # ── Zone management ───────────────────────────────────────────

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

    def get_zone(self) -> EncounterZone | None:
        return self._zone

    # ── Post-battle MC tagging ────────────────────────────────────

    @staticmethod
    def add_mc_drops(repository: RepositoryState, mc_drops: list[dict]) -> None:
        """
        Called by BattleScene after victory to add MC drops to the repository.
        Ensures magic_core tag is set on every MC item.
        """
        for mc in mc_drops:
            size    = mc.get("size", "S").lower()
            qty     = mc.get("qty", 1)
            item_id = f"mc_{size}"
            _add_mc(repository, item_id, qty)

    # ── Party fill ────────────────────────────────────────────────

    def fill_party(
        self, state: BattleState, party: PartyState, flags: set[str]
    ) -> BattleState:
        state.party = [self._member_to_combatant(m, flags) for m in party.members]
        state.build_turn_order()
        return state

    def _member_to_combatant(self, member: MemberState, flags: set[str]) -> Combatant:
        abilities = self._load_class_abilities(member.class_name, member.level, flags)
        totals = (
            stat_totals(member, self._item_catalog)
            if self._item_catalog is not None
            else {"str": member.str_, "dex": member.dex, "con": member.con, "int": member.int_}
        )
        return Combatant(
            id=member.id,
            name=member.name,
            hp=member.hp,
            hp_max=member.hp_max,
            mp=member.mp,
            mp_max=member.mp_max,
            atk=totals["str"],
            def_=totals["con"],
            mres=totals["int"],
            dex=totals["dex"],
            is_enemy=False,
            portrait_path=f"assets/images/{member.id}_profile.png",
            abilities=abilities,
        )

    def _load_class_abilities(
        self, class_name: str, level: int, flags: set[str]
    ) -> list[dict]:
        """Load abilities from class YAML, filtered by unlock_level and unlock_flag.

        An ability with `unlock_flag` set is only returned when that flag is
        present in `flags`. Abilities without `unlock_flag` are unaffected.
        """
        if class_name in self._class_cache:
            all_abs = self._class_cache[class_name]
        else:
            if not self._classes_dir:
                return []
            path = self._classes_dir / f"{class_name}.yaml"
            if not path.exists():
                return []
            with open(path) as f:
                data = yaml.safe_load(f)
            all_abs = data.get("abilities", [])
            self._class_cache[class_name] = all_abs
        result = []
        for ab in all_abs:
            if ab["unlock_level"] > level:
                continue
            unlock_flag = ab.get("unlock_flag")
            if unlock_flag and unlock_flag not in flags:
                continue
            result.append(ab)
        return result
