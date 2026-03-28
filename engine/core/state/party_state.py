# engine/core/state/party_state.py
#
# Extended stub — adds display fields needed by StatusScene.
# Full battle stats, formation, row logic added in Phase 4.

from __future__ import annotations
import math


class MemberState:
    """
    Holds all per-member state needed for display and battle (Phase 4).
    Fields marked stub will be populated from character YAML in Phase 5.
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
        hp: int = 308,
        hp_max: int = 308,
        mp: int = 10,
        mp_max: int = 10,
        str_: int = 208, # Debug value
        dex: int = 70,
        con: int = 80,
        int_: int = 5,
        equipped: dict | None = None,
    ) -> None:
        self.id         = member_id
        self.name       = name
        self.protagonist = protagonist
        self.class_name = class_name
        self.level      = level
        self.exp        = exp
        self.exp_next   = exp_next
        self.hp         = hp
        self.hp_max     = hp_max
        self.mp         = mp
        self.mp_max     = mp_max
        self.str_       = str_
        self.dex        = dex
        self.con        = con
        self.int_       = int_
        self.equipped: dict = equipped or {}   # {slot: item_name_str}

    @property
    def exp_pct(self) -> float:
        """0.0 – 1.0 progress toward next level."""
        if self.exp_next <= 0:
            return 1.0
        return min(self.exp / self.exp_next, 1.0)

    def __repr__(self) -> str:
        tag = " [protagonist]" if self.protagonist else ""
        return f"MemberState({self.id!r}, name={self.name!r}{tag})"


class PartyState:
    """
    Holds party member list.
    Full logic (formation, row, exp, level-up) added in Phase 4.
    """

    def __init__(self) -> None:
        self._members: list[MemberState] = []

    # ── Mutation ──────────────────────────────────────────────

    def add_member(self, member: MemberState) -> None:
        self._members.append(member)

    def set_protagonist_name(self, name: str) -> None:
        for m in self._members:
            if m.protagonist:
                m.name = name
                return

    # ── Query ─────────────────────────────────────────────────

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
