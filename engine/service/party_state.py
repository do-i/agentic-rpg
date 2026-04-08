# engine/service/party_state.py
#
# Stat calculation helpers operating on MemberState.
# MemberState and PartyState data classes live in engine/dto/.

from __future__ import annotations
import math

from engine.dto.member_state import MemberState
from engine.dto.party_state import PartyState

# EXP formula constants — mirrors battle_rewards.py
_CLASS_EXP_BASE: dict[str, int] = {
    "hero":     100,
    "warrior":  110,
    "sorcerer":  95,
    "cleric":    95,
    "rogue":     90,
}
_EXP_FACTOR = 2.0
LEVEL_CAP   = 100

# Stat keys that have growth tables in class YAML
GROWTH_STATS = ("str", "dex", "con", "int")


def calc_exp_next(class_name: str, level: int) -> int:
    """EXP required to reach level+1. Returns 0 at level cap."""
    if level >= LEVEL_CAP:
        return 0
    base = _CLASS_EXP_BASE.get(class_name.lower(), 100)
    return int(base * math.pow(level + 1, _EXP_FACTOR))


def stat_gain_at(member: MemberState, stat: str, level: int) -> int:
    """
    Returns the growth value for a stat at the given level.
    Cycles modulo 10 (len of growth table). Returns 0 if not loaded.
    level is the NEW level just reached (1-indexed).
    """
    if member.stat_growth is None:
        return 0
    table = member.stat_growth[stat]
    return table[(level - 1) % len(table)]


def recalc_exp_next(member: MemberState) -> None:
    """Call after any level or class_name change."""
    member.exp_next = calc_exp_next(member.class_name, member.level)


def exp_pct(member: MemberState) -> float:
    if member.exp_next <= 0:
        return 1.0
    return min(member.exp / member.exp_next, 1.0)
