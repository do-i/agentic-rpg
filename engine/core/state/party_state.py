# engine/core/state/party_state.py

from __future__ import annotations


class MemberState:
    """
    Holds all per-member state for display, battle, and save/load.
    All fields are real game values — no debug overrides here.
    """

    def __init__(
        self,
        member_id: str,
        name: str,
        protagonist: bool = False,
        class_name: str = "",
        level: int = 1,
        exp: int = 0,
        exp_next: int = 100,
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
        self.exp_next    = exp_next
        self.hp          = hp
        self.hp_max      = hp_max
        self.mp          = mp
        self.mp_max      = mp_max
        self.str_        = str_
        self.dex         = dex
        self.con         = con
        self.int_        = int_
        self.equipped: dict = equipped or {}

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
