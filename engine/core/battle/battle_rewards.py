# engine/core/battle/battle_rewards.py
#
# Phase 4 — Battle system

from __future__ import annotations
import math
from dataclasses import dataclass, field

from engine.core.battle.combatant import Combatant
from engine.core.state.party_state import PartyState, MemberState, _calc_exp_next

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


@dataclass
class LevelUpResult:
    member_id:   str
    member_name: str
    old_level:   int
    new_level:   int
    hp_gained:   int
    mp_gained:   int
    str_gained:  int
    dex_gained:  int
    con_gained:  int
    int_gained:  int


@dataclass
class MemberExpResult:
    member_id:   str
    member_name: str
    exp_gained:  int
    level_ups:   list[LevelUpResult] = field(default_factory=list)


@dataclass
class LootResult:
    """Stub — full loot table resolution in Phase 4 follow-up."""
    mc_drops:   list[dict] = field(default_factory=list)
    item_drops: list[dict] = field(default_factory=list)
    gp_gained:  int = 0


@dataclass
class BattleRewards:
    total_exp:      int
    member_results: list[MemberExpResult]
    loot:           LootResult
    boss_flag:      str = ""


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
            str_gain = member.stat_gain_at("str", new_level)
            dex_gain = member.stat_gain_at("dex", new_level)
            con_gain = member.stat_gain_at("con", new_level)
            int_gain = member.stat_gain_at("int", new_level)

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

            member.recalc_exp_next()

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
        """Stub — full weighted loot table in Phase 4 follow-up."""
        mc_drops = [{"size": "S", "qty": 1} for _ in enemies]
        return LootResult(mc_drops=mc_drops)

    @staticmethod
    def _is_ko(member: MemberState) -> bool:
        return getattr(member, "hp", 1) <= 0
