# engine/core/state/party_state.py
#
# STUB — full implementation in Phase 4 (battle system)
# For now: holds protagonist name only.


class MemberState:
    """Stub — minimal member data needed before battle system is built."""

    def __init__(self, member_id: str, name: str, protagonist: bool = False) -> None:
        self.id = member_id
        self.name = name
        self.protagonist = protagonist
        # Full stats, equipment, abilities etc. added in Phase 4

    def __repr__(self) -> str:
        tag = " [protagonist]" if self.protagonist else ""
        return f"MemberState({self.id!r}, name={self.name!r}{tag})"


class PartyState:
    """
    Stub — holds party member list.
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
