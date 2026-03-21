# engine/core/state/game_state.py

from engine.core.state.flag_state import FlagState
from engine.core.state.map_state import MapState
from engine.core.state.playtime import Playtime
from engine.core.state.party_state import PartyState, MemberState
from engine.core.state.repository_state import RepositoryState
from engine.core.models.position import Position


class GameState:
    """
    Thin aggregator — owns no logic itself.
    All mutation and retrieval delegated to sub-modules.
    """

    def __init__(self) -> None:
        self.flags = FlagState()
        self.map = MapState()
        self.playtime = Playtime()
        self.party = PartyState()
        self.repository = RepositoryState()

    # ── Factory: New Game ─────────────────────────────────────

    @classmethod
    def from_new_game(cls, manifest: dict, protagonist_name: str) -> "GameState":
        """
        Bootstrap a fresh game state from manifest + player-entered name.
        """
        state = cls()

        # flags
        bootstrap_flags = manifest.get("bootstrap_flags", [])
        state.flags.add_flags(bootstrap_flags)

        # protagonist
        proto = manifest.get("protagonist", {})
        member = MemberState(
            member_id=proto.get("id", "protagonist"),
            name=protagonist_name,
            protagonist=True,
        )
        state.party.add_member(member)

        # starting map
        start = manifest.get("start", {})
        state.map.move_to(
            map_id=start.get("map", ""),
            position=Position.from_list(start.get("position", [0, 0])),
        )

        # playtime starts at 0, begin session
        state.playtime.start_session()

        return state

    # ── Factory: Load Game ────────────────────────────────────

    @classmethod
    def from_save(cls, save: dict) -> "GameState":
        """
        Restore state from a save file dict.
        Full implementation in Phase 3 (save/load).
        """
        state = cls()
        state.flags = FlagState.from_set(set(save.get("flags", [])))
        state.map = MapState.from_dict(save.get("map", {}))
        state.playtime = Playtime.from_seconds(
            save.get("meta", {}).get("playtime_seconds", 0)
        )
        state.playtime.start_session()
        for m in save.get("party", []):
            state.party.add_member(MemberState(
                member_id=m.get("id", ""),
                name=m.get("name", ""),
                protagonist=m.get("protagonist", False),
            ))
        return state

    def __repr__(self) -> str:
        return (
            f"GameState("
            f"flags={len(self.flags.to_list())}, "
            f"map={self.map.current!r}, "
            f"playtime={self.playtime.display})"
        )