# engine/core/state/party_state.py

from __future__ import annotations
import math

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


def _calc_exp_next(class_name: str, level: int) -> int:
    """EXP required to reach level+1. Returns 0 at level cap."""
    if level >= LEVEL_CAP:
        return 0
    base = _CLASS_EXP_BASE.get(class_name.lower(), 100)
    return int(base * math.pow(level + 1, _EXP_FACTOR))


class MemberState:
    """
    Holds all per-member state for display, battle, and save/load.

    stat_growth: dict loaded from class YAML, e.g.:
        {"str": [3,2,3,...], "dex": [2,2,...], "con": [2,3,...], "int": [1,1,...]}
    Each list is 10 entries, cycled via modulo on level-up.
    Set via load_stat_growth() at party join or load time.
    """

    def __init__(
        self,
        member_id: str,
        name: str,
        protagonist: bool,
        class_name: str,
        level: int,
        exp: int,
        hp: int,
        hp_max: int,
        mp: int,
        mp_max: int,
        str_: int,
        dex: int,
        con: int,
        int_: int,
        equipped: dict,
        exp_next: int = None,
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
        self.equipped    = equipped

        # stat_growth loaded from class YAML — None until load_stat_growth() called
        self._stat_growth: dict[str, list[int]] | None = None

        self.exp_next: int = (
            exp_next if exp_next is not None
            else _calc_exp_next(class_name, level)
        )

    def load_stat_growth(self, class_data: dict) -> None:
        """
        Cache stat_growth from the class YAML dict.
        Call at party join and after load_game.
        Expected class_data shape:
            {"stat_growth": {"str": [...], "dex": [...], "con": [...], "int": [...]}}
        """
        growth = class_data.get("stat_growth", {})
        self._stat_growth = {
            "str": growth["str"],
            "dex": growth["dex"],
            "con": growth["con"],
            "int": growth["int"],
        }

    def stat_gain_at(self, stat: str, level: int) -> int:
        """
        Returns the growth value for a stat at the given level.
        Cycles modulo 10 (len of growth table). Returns 0 if not loaded.
        level is the NEW level just reached (1-indexed).
        """
        if self._stat_growth is None:
            return 0
        table = self._stat_growth[stat]
        return table[(level - 1) % len(table)]

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
