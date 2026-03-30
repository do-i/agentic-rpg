# engine/core/state/party_state.py

from __future__ import annotations
import math

# EXP formula constants — mirrors battle_rewards.py
# exp_required(level) = base * (level ^ 2.0)
_CLASS_EXP_BASE: dict[str, int] = {
    "hero":     100,
    "warrior":  110,
    "sorcerer":  95,
    "cleric":    95,
    "rogue":     90,
}
_EXP_FACTOR = 2.0
LEVEL_CAP   = 100


def _calc_exp_next(class_name: str, level: int) -> int:
    """EXP required to reach level+1. Returns 0 at level cap."""
    if level >= LEVEL_CAP:
        return 0
    base = _CLASS_EXP_BASE.get(class_name.lower(), 100)
    return int(base * math.pow(level + 1, _EXP_FACTOR))


class MemberState:
    """
    Holds all per-member state for display, battle, and save/load.
    exp_next is stored (matches save schema) and recalculated on init
    and every level-up via recalc_exp_next().
    """

    def __init__(
        self,
        member_id: str,
        name: str,
        protagonist: bool = False,
        class_name: str = "",
        level: int = 1,
        exp: int = 0,
        exp_next: int | None = None,   # None → auto-calculate from class+level
        hp: int = 20,
        hp_max: int = 20,
        mp: int = 0,
        mp_max: int = 0,
        str_: int = 10,
        dex: int = 10,
        con: int = 10,
        int_: int = 10,
        equipped: dict | None = None,
    ) -> None:
        self.id          = member_id
        self.name        = name
        self.protagonist = protagonist
        self.class_name  = class_name
        self.level       = level
        self.exp         = exp
        self.hp          = hp
        self.hp_max      = hp_max
        self.mp          = mp
        self.mp_max      = mp_max
        self.str_        = str_
        self.dex         = dex
        self.con         = con
        self.int_        = int_
        self.equipped: dict = equipped or {}

        # stored field — recalculated whenever level or class changes
        self.exp_next: int = (
            exp_next if exp_next is not None
            else _calc_exp_next(class_name, level)
        )

    def recalc_exp_next(self) -> None:
        """Call after any level or class_name change."""
        self.exp_next = _calc_exp_next(self.class_name, self.level)

    @property
    def exp_pct(self) -> float:
        if self.exp_next <= 0:
            return 1.0
        return min(self.exp / self.exp_next, 1.0)

    def __repr__(self) -> str:
        tag = " [protagonist]" if self.protagonist else ""
        return f"MemberState({self.id!r}, name={self.name!r}{tag})"


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
