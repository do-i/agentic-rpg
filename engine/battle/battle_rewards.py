# engine/battle/battle_rewards.py
#
# Battle reward logic — EXP split, level-ups, loot resolution.
# DTOs live in engine.battle.battle_rewards_data.

from __future__ import annotations
import math

from engine.battle.combatant import Combatant
from engine.util.pseudo_random import PseudoRandom
from engine.util.weighted_pick import weighted_pick
from engine.party.party_state import (
    PartyState, calc_exp_next, stat_gain_at, recalc_exp_next,
    _FALLBACK_EXP_BASE, _FALLBACK_EXP_FACTOR, LEVEL_CAP,
)
from engine.party.member_state import MemberState
from engine.settings.balance_data import BalanceData
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
    "EXP_CAP",
    "LEVEL_CAP",
]

# Default EXP cap — authoritative value comes from the scenario balance YAML
# and flows into RewardCalculator via DI. LEVEL_CAP is re-exported from
# party_state to keep it single-sourced.
EXP_CAP = 1_000_000


def exp_required(class_name: str, level: int) -> int:
    """Legacy helper that accepts a bare class_name. Uses the fallback
    per-class EXP base + factor from party_state (kept for tests)."""
    base = _FALLBACK_EXP_BASE.get(class_name.lower(), 100)
    return int(base * math.pow(level, _FALLBACK_EXP_FACTOR))


class RewardCalculator:
    """
    Computes EXP split, applies level-ups with stat_growth, resolves loot.
    """

    def __init__(self, rng: PseudoRandom, balance: BalanceData | None = None) -> None:
        self._rng       = rng
        self._level_cap = balance.level_cap if balance else LEVEL_CAP
        self._exp_cap   = balance.exp_cap   if balance else EXP_CAP

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
        if member.level >= self._level_cap:
            return []

        member.exp = min(member.exp + amount, self._exp_cap)
        level_ups  = []

        while member.level < self._level_cap:
            needed = self._exp_required(member, member.level + 1)
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

            recalc_exp_next(member, level_cap=self._level_cap)

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

    def _exp_required(self, member: MemberState, level: int) -> int:
        """EXP required to *reach* the given level. Uses the member's
        per-class exp_base/exp_factor if loaded, else the fallback table."""
        base   = member.exp_base   or _FALLBACK_EXP_BASE.get(
            member.class_name.lower(), 100)
        factor = member.exp_factor or _FALLBACK_EXP_FACTOR
        return int(base * math.pow(level, factor))

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
                entry = weighted_pick(self._rng, pool, lambda e: e.get("weight", 1))
                item_id = entry.get("item", "") if entry else ""
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


