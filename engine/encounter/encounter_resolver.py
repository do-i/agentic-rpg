# engine/encounter/encounter_resolver.py

from __future__ import annotations

from engine.encounter.encounter_zone_data import EncounterZone, Formation
from engine.battle.enemy_loader import EnemyLoader
from engine.battle.combatant import Combatant
from engine.battle.battle_state import BattleState
from engine.common.flag_state import FlagState
from engine.util.pseudo_random import PseudoRandom


class EncounterResolver:
    """
    Picks formations and builds BattleState objects for the visible enemy system.

    Used by EnemySpawner to pick which formation a spawned enemy represents,
    and by WorldMapScene to build a BattleState when the player collides with one.
    """

    def __init__(self, enemy_loader: EnemyLoader, rng: PseudoRandom) -> None:
        self._enemy_loader = enemy_loader
        self._rng = rng

    # ── Formation selection ───────────────────────────────────────

    def pick_formation(self, zone: EncounterZone) -> Formation | None:
        """Pick a random weighted formation from the zone's entry list."""
        if not zone.entries.entries:
            return None
        return self._weighted_pick(zone.entries.entries)

    def _weighted_pick(self, entries: list[Formation]) -> Formation | None:
        total = sum(e.weight for e in entries)
        if total == 0:
            return None
        roll = self._rng.randint(1, 100)
        cumulative = 0
        for entry in entries:
            cumulative += int(entry.weight * 100 / total)
            if roll <= cumulative:
                return entry
        return entries[-1]

    # ── Battle state construction ─────────────────────────────────

    def build_battle_from_formation(
        self,
        formation: Formation,
        zone: EncounterZone,
        inventory_item_ids: set[str],
    ) -> BattleState | None:
        """
        Build a BattleState from a specific formation. Called when the player
        physically collides with a visible enemy sprite.
        """
        enemies, barrier_messages = self._build_enemies(formation, zone, inventory_item_ids)
        if not enemies:
            return None
        state = BattleState(party=[], enemies=enemies)
        state.barrier_messages = barrier_messages
        state.background = zone.background
        return state

    def build_battle_from_boss(
        self,
        zone: EncounterZone,
        flags: FlagState,
    ) -> BattleState | None:
        """
        Build a BattleState for the zone boss. Returns None if boss already defeated.
        Kept for use by EnemySpawner when the player collides with the boss sprite.
        """
        boss = zone.boss
        if not boss:
            return None
        if boss.once and boss.flag_set and flags.has_flag(boss.flag_set):
            return None

        enemy = self._enemy_loader.load(boss.enemy_id)
        if not enemy:
            return None

        state = BattleState(party=[], enemies=[enemy])
        state.boss_flag = boss.flag_set
        state.background = zone.background
        return state

    # ── Enemy building ────────────────────────────────────────────

    def _build_enemies(
        self,
        formation: Formation,
        zone: EncounterZone,
        inventory_item_ids: set[str],
    ) -> tuple[list[Combatant], list[str]]:
        barrier_map = {b.enemy_id: b for b in zone.barrier_enemies}
        result = []
        barrier_messages = []
        for enemy_id in formation.enemy_ids:
            barrier = barrier_map.get(enemy_id)
            if barrier and barrier.requires_item not in inventory_item_ids:
                barrier_messages.append(barrier.blocked_message)
                continue
            combatant = self._enemy_loader.load(enemy_id)
            if combatant:
                result.append(combatant)
        return result, barrier_messages
