# engine/dto/game_state.py

from engine.common.flag_state import FlagState
from engine.common.map_state import MapState
from engine.util.playtime import Playtime
from engine.common.party_state import PartyState
from engine.party.repository_state import RepositoryState


class GameState:
    """
    Thin aggregator — owns no logic itself.
    All mutation and retrieval delegated to sub-modules.
    """

    def __init__(self) -> None:
        self.flags      = FlagState()
        self.map        = MapState()
        self.playtime   = Playtime()
        self.party      = PartyState()
        self.repository = RepositoryState()

    def __repr__(self) -> str:
        return (
            f"GameState("
            f"flags={len(self.flags.to_list())}, "
            f"map={self.map.current!r}, "
            f"playtime={self.playtime.display})"
        )
