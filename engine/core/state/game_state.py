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
        self.flags      = FlagState()
        self.map        = MapState()
        self.playtime   = Playtime()
        self.party      = PartyState()
        self.repository = RepositoryState()

    # ── Factory: New Game ─────────────────────────────────────

    @classmethod
    def from_new_game(cls, manifest: dict, protagonist_name: str) -> "GameState":
        state = cls()

        bootstrap_flags = manifest.get("bootstrap_flags", [])
        state.flags.add_flags(bootstrap_flags)

        proto = manifest.get("protagonist", {})
        member = MemberState(
            member_id=proto.get("id", "protagonist"),
            name=protagonist_name,
            protagonist=True,
            class_name=proto.get("class", "hero"),
            # exp_next auto-calculated from class + level=1
        )
        state.party.add_member(member)

        start = manifest.get("start", {})
        state.map.move_to(
            map_id=start.get("map", ""),
            position=Position.from_list(start.get("position", [0, 0])),
        )

        state.playtime.start_session()
        return state

    # ── Factory: Load Game ────────────────────────────────────

    @classmethod
    def from_save(cls, save: dict) -> "GameState":
        state = cls()
        state.flags    = FlagState.from_set(set(save["flags"]))
        state.map      = MapState.from_dict(save["map"])
        state.playtime = Playtime.from_seconds(save["meta"]["playtime_seconds"])
        state.playtime.start_session()

        for m in save["party"]:
            member = MemberState(
                member_id=m["id"],
                name=m["name"],
                protagonist=m["protagonist"],
                class_name=m["class"],
                level=m["level"],
                exp=m["exp"],
                exp_next=m.get("exp_next"),   # optional — recalculated if absent
                hp=m["hp"],
                hp_max=m["hp_max"],
                mp=m["mp"],
                mp_max=m["mp_max"],
                str_=m["str"],
                dex=m["dex"],
                con=m["con"],
                int_=m["int"],
                equipped=m["equipped"],
            )
            state.party.add_member(member)

        return state

    def __repr__(self) -> str:
        return (
            f"GameState("
            f"flags={len(self.flags.to_list())}, "
            f"map={self.map.current!r}, "
            f"playtime={self.playtime.display})"
        )
