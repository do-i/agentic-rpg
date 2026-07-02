# engine/party/party_state.py
#
# Party data + stat calculation helpers.

from __future__ import annotations
import math

from engine.party.member_state import MemberState


class PartyState:
    """Holds the active party member list."""

    def __init__(self) -> None:
        self._members: list[MemberState] = []

    def add_member(self, member: MemberState) -> None:
        self._members.append(member)

    def set_protagonist_name(self, name: str) -> None:
        for m in self._members:
            if m.protagonist:
                m.name = name
                return

    @property
    def members(self) -> list[MemberState]:
        return list(self._members)

    @property
    def protagonist(self) -> MemberState | None:
        for m in self._members:
            if m.protagonist:
                return m
        return None

    def __repr__(self) -> str:
        return f"PartyState({self._members})"


# ── Stat calculation helpers ─────────────────────────────────

# Default cap — authoritative value lives in the scenario balance YAML
# and is injected into RewardCalculator at runtime.
LEVEL_CAP = 100

# Stat keys that have growth tables in class YAML
GROWTH_STATS = ("str", "dex", "con", "int")

def calc_exp_next(
    member: MemberState,
    level: int,
    level_cap: int = LEVEL_CAP,
) -> int:
    """EXP required to reach level+1. Returns 0 at level cap.

    Uses the member's exp_base/exp_factor cached from the class YAML —
    load_class_data() must have run (party join / load_game).
    """
    if level >= level_cap:
        return 0
    return int(member.exp_curve_base() * math.pow(level + 1, member.exp_curve_factor()))


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


def recalc_exp_next(member: MemberState, level_cap: int = LEVEL_CAP) -> None:
    """Call after any level or class_name change."""
    member.exp_next = calc_exp_next(member, member.level, level_cap=level_cap)


def exp_pct(member: MemberState) -> float:
    if member.exp_next <= 0:
        return 1.0
    return min(member.exp / member.exp_next, 1.0)
