# engine/battle/battle_rewards.py
#
# Battle reward logic — EXP split, level-ups, loot resolution.
# DTOs live in engine.battle.battle_rewards_data.

from __future__ import annotations
import math
import random

from engine.battle.combatant import Combatant
from engine.party.party_state import PartyState
from engine.party.member_state import MemberState
from engine.party.party_state import calc_exp_next, stat_gain_at, recalc_exp_next
from engine.battle.battle_rewards_data import (
    LevelUpResult,
    MemberExpResult,
    LootResult,
    BattleRewards,
)

# Re-export so existing imports keep working
__all__ = [
    "exp_required",
    "LevelUpResult",
    "MemberExpResult",
    "LootResult",
    "BattleRewards",
    "RewardCalculator",
]

EXP_CAP   = 1_000_000
LEVEL_CAP = 100

CLASS_EXP_BASE = {
    "hero":     100,
    "warrior":  110,
    "sorcerer":  95,
    "cleric":    95,
    "rogue":     90,
}
EXP_FACTOR = 2.0


def exp_required(class_name: str, level: int) -> int:
    base = CLASS_EXP_BASE.get(class_name.lower(), 100)
    return int(base * math.pow(level, EXP_FACTOR))


class RewardCalculator:
    """
    Computes EXP split, applies level-ups with stat_growth, resolves loot.
    """

    def calculate(
        self,
        enemies: list[Combatant],
        party: PartyState,
        boss_flag: str = "",
    ) -> BattleRewards:
        total_exp = sum(getattr(e, "exp_yield", 0) for e in enemies)
        living    = [m for m in party.members if not self._is_ko(m)]
        share     = total_exp // max(len(living), 1)

        member_results = []
        for member in party.members:
            if self._is_ko(member):
                member_results.append(MemberExpResult(
                    member_id=member.id,
                    member_name=member.name,
                    exp_gained=0,
                ))
                continue
            level_ups = self._apply_exp(member, share)
            member_results.append(MemberExpResult(
                member_id=member.id,
                member_name=member.name,
                exp_gained=share,
                level_ups=level_ups,
            ))

        return BattleRewards(
            total_exp=total_exp,
            member_results=member_results,
            loot=self._resolve_loot(enemies),
            boss_flag=boss_flag,
        )

    # ── EXP & level-up ───────────────────────────────────────

    def _apply_exp(self, member: MemberState, amount: int) -> list[LevelUpResult]:
        if member.level >= LEVEL_CAP:
            return []

        member.exp = min(member.exp + amount, EXP_CAP)
        level_ups  = []

        while member.level < LEVEL_CAP:
            needed = exp_required(member.class_name, member.level + 1)
            if member.exp < needed:
                break

            old_level = member.level
            member.level += 1
            new_level = member.level

            # stat growth — modulo cycles the 10-entry table
            str_gain = stat_gain_at(member, "str", new_level)
            dex_gain = stat_gain_at(member, "dex", new_level)
            con_gain = stat_gain_at(member, "con", new_level)
            int_gain = stat_gain_at(member, "int", new_level)

            member.str_ += str_gain
            member.dex  += dex_gain
            member.con  += con_gain
            member.int_ += int_gain

            # HP/MP growth uses post-growth CON and INT
            hp_gain = member.con + 6
            mp_gain = member.int_ + 6

            member.hp_max += hp_gain
            member.mp_max += mp_gain
            member.hp = member.hp_max   # full restore on level-up
            member.mp = member.mp_max

            recalc_exp_next(member)

            level_ups.append(LevelUpResult(
                member_id=member.id,
                member_name=member.name,
                old_level=old_level,
                new_level=new_level,
                hp_gained=hp_gain,
                mp_gained=mp_gain,
                str_gained=str_gain,
                dex_gained=dex_gain,
                con_gained=con_gain,
                int_gained=int_gain,
            ))

        return level_ups

    # ── Loot ─────────────────────────────────────────────────

    def _resolve_loot(self, enemies: list[Combatant]) -> LootResult:
        """Resolve loot from enemy drop tables.

        Each enemy may define drops.mc (guaranteed magic cores) and
        drops.loot (weighted item pools — one roll per pool).
        """
        # Aggregate MC drops by size
        mc_totals: dict[str, int] = {}
        item_totals: dict[str, int] = {}

        for enemy in enemies:
            drops = enemy.drops
            if not drops:
                continue

            # MC drops — guaranteed
            for mc in drops.get("mc", []):
                size = mc.get("size", "S")
                qty = mc.get("qty", 1)
                mc_totals[size] = mc_totals.get(size, 0) + qty

            # Loot pools — one weighted roll per pool
            for pool_entry in drops.get("loot", []):
                pool = pool_entry.get("pool", [])
                if not pool:
                    continue
                item_id = _weighted_pick(pool)
                if item_id:
                    item_totals[item_id] = item_totals.get(item_id, 0) + 1

        mc_drops = [{"size": s, "qty": q} for s, q in mc_totals.items()]
        item_drops = [
            {"id": iid, "name": iid.replace("_", " ").title(), "qty": q}
            for iid, q in item_totals.items()
        ]

        return LootResult(mc_drops=mc_drops, item_drops=item_drops)

    @staticmethod
    def _is_ko(member: MemberState) -> bool:
        return getattr(member, "hp", 1) <= 0


def _weighted_pick(pool: list[dict]) -> str | None:
    """Pick one item id from a weighted pool. Returns None if pool is empty."""
    if not pool:
        return None
    items = [entry.get("item", "") for entry in pool]
    weights = [entry.get("weight", 1) for entry in pool]
    return random.choices(items, weights=weights, k=1)[0]
