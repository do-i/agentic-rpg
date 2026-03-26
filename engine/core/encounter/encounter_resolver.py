# engine/core/encounter/encounter_resolver.py
#
# Phase 4 — Battle system

from __future__ import annotations
import random
from pathlib import Path

from engine.core.encounter.encounter_zone import EncounterZone, Formation
from engine.core.encounter.enemy_loader import EnemyLoader
from engine.core.battle.combatant import Combatant
from engine.core.battle.battle_state import BattleState
from engine.core.state.flag_state import FlagState


class EncounterResolver:
    """
    Decides whether a random encounter triggers, picks the formation,
    filters barrier enemies, and builds a BattleState ready for BattleScene.

    Resolution algorithm (matches docs/03-Battle.md + docs/11-Loot.md):
      Roll 1 — encounter trigger:
        roll D100 <= final_encounter_rate * 100  → encounter fires
      Roll 2 — set selection:
        50/50 between set_a and set_b
      Roll 3 — formation:
        weighted walk, first entry where cumulative_weight >= roll
      Barrier filter:
        any barrier enemy in formation without required item → swap/skip
    """

    def __init__(self, enemy_loader: EnemyLoader) -> None:
        self._enemy_loader = enemy_loader

    # ── Public API ────────────────────────────────────────────

    def try_random_encounter(
        self,
        zone: EncounterZone,
        encounter_modifier: float,
        flags: FlagState,
        inventory_item_ids: set[str],
    ) -> BattleState | None:
        """
        Returns a BattleState if an encounter triggers, None otherwise.
        encounter_modifier: from Rogue passive / accessories (can be negative).
        """
        final_rate = max(0.0, min(1.0, zone.encounter_rate + encounter_modifier))
        roll = random.randint(1, 100)
        if roll > int(final_rate * 100):
            return None

        formation = self._pick_formation(zone)
        if not formation:
            return None

        enemies = self._build_enemies(
            formation, zone, inventory_item_ids
        )
        if not enemies:
            return None

        return BattleState(party=[], enemies=enemies)   # party filled by caller

    def try_boss_encounter(
        self,
        zone: EncounterZone,
        flags: FlagState,
    ) -> BattleState | None:
        """
        Returns BattleState for the zone boss if it should trigger.
        Boss is once:true — skipped if completion flag already set.
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
        return state

    # ── Formation selection ───────────────────────────────────

    def _pick_formation(self, zone: EncounterZone) -> Formation | None:
        # 50/50 set choice
        chosen_set = zone.set_a if random.random() < 0.5 else zone.set_b
        if not chosen_set.entries:
            return None
        return self._weighted_pick(chosen_set.entries)

    @staticmethod
    def _weighted_pick(entries: list[Formation]) -> Formation | None:
        total = sum(e.weight for e in entries)
        if total == 0:
            return None
        roll = random.randint(1, 100)
        # normalise weights to 100 if they don't already sum to 100
        cumulative = 0
        for entry in entries:
            cumulative += int(entry.weight * 100 / total)
            if roll <= cumulative:
                return entry
        return entries[-1]   # fallback: last entry

    # ── Enemy building ────────────────────────────────────────

    def _build_enemies(
        self,
        formation: Formation,
        zone: EncounterZone,
        inventory_item_ids: set[str],
    ) -> list[Combatant]:
        barrier_map = {b.enemy_id: b for b in zone.barrier_enemies}
        result = []
        for enemy_id in formation.enemy_ids:
            barrier = barrier_map.get(enemy_id)
            if barrier and barrier.requires_item not in inventory_item_ids:
                # barrier enemy present but player lacks required item — skip it
                # the blocked_message is surfaced by BattleScene stub — Phase 4
                continue
            combatant = self._enemy_loader.load(enemy_id)
            if combatant:
                result.append(combatant)
        return result
