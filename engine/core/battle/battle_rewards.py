# engine/core/battle/battle_rewards.py
#
# Phase 4 — Battle system

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field

from engine.core.battle.combatant import Combatant
from engine.core.state.party_state import PartyState, MemberState, _calc_exp_next


# ── EXP formula (docs/02-Characters.md) ──────────────────────
# exp_required(level) = exp_base * (level ^ exp_factor)
# KO'd members receive 0 EXP. EXP shared equally among living.

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


@dataclass
class MemberExpResult:
    member_id:   str
    member_name: str
    exp_gained:  int
    level_ups:   list[LevelUpResult] = field(default_factory=list)


@dataclass
class LootResult:
    """Stub — full loot table resolution in Phase 4 follow-up."""
    mc_drops:   list[dict] = field(default_factory=list)   # [{size, qty}]
    item_drops: list[dict] = field(default_factory=list)   # [{id, name, qty}]
    gp_gained:  int = 0


@dataclass
class BattleRewards:
    total_exp:       int
    member_results:  list[MemberExpResult]
    loot:            LootResult
    boss_flag:       str = ""   # set_flag from boss on_complete, if any


class RewardCalculator:
    """
    Computes EXP split, applies level-ups, and resolves loot drops
    after a victorious battle.
    """

    def calculate(
        self,
        enemies: list[Combatant],
        party: PartyState,
        boss_flag: str = "",
    ) -> BattleRewards:
        total_exp = sum(getattr(e, "exp_yield", 0) for e in enemies)
        living = [m for m in party.members if not self._is_ko(m)]
        share = total_exp // max(len(living), 1)

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

        loot = self._resolve_loot(enemies)

        return BattleRewards(
            total_exp=total_exp,
            member_results=member_results,
            loot=loot,
            boss_flag=boss_flag,
        )

    # ── EXP & level-up ───────────────────────────────────────

    def _apply_exp(self, member: MemberState, amount: int) -> list[LevelUpResult]:
        if member.level >= LEVEL_CAP:
            return []

        member.exp = min(member.exp + amount, EXP_CAP)
        level_ups = []

        while member.level < LEVEL_CAP:
            # threshold to reach the NEXT level
            needed = exp_required(member.class_name, member.level + 1)
            if member.exp < needed:
                break

            old_level = member.level
            member.level += 1
            hp_gain, mp_gain = self._stat_gains(member)
            member.hp_max += hp_gain
            member.mp_max += mp_gain
            member.hp = member.hp_max   # full restore on level-up
            member.mp = member.mp_max

            # keep stored exp_next in sync with new level
            member.recalc_exp_next()

            level_ups.append(LevelUpResult(
                member_id=member.id,
                member_name=member.name,
                old_level=old_level,
                new_level=member.level,
                hp_gained=hp_gain,
                mp_gained=mp_gain,
            ))

        return level_ups

    def _stat_gains(self, member: MemberState) -> tuple[int, int]:
        """HP gain = CON + 6, MP gain = INT + 6  (docs/02-Characters.md)."""
        con  = getattr(member, "con",  8)
        int_ = getattr(member, "int_", 6)
        return con + 6, int_ + 6

    # ── Loot ─────────────────────────────────────────────────

    def _resolve_loot(self, enemies: list[Combatant]) -> LootResult:
        """
        Stub — rolls one item drop per enemy loot pool.
        Full weighted loot table resolution in Phase 4 follow-up.
        """
        mc_drops: list[dict] = []
        item_drops: list[dict] = []

        for enemy in enemies:
            # MC drop — always guaranteed (docs/10-Enemy.md)
            mc_drops.append({"size": "S", "qty": 1})   # stub — Phase 4

        return LootResult(mc_drops=mc_drops, item_drops=item_drops)

    @staticmethod
    def _is_ko(member: MemberState) -> bool:
        return getattr(member, "hp", 1) <= 0
