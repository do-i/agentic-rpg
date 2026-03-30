# engine/core/state/game_state.py

import yaml
from engine.core.state.flag_state import FlagState
from engine.core.state.map_state import MapState
from engine.core.state.playtime import Playtime
from engine.core.state.party_state import PartyState, MemberState
from engine.core.state.repository_state import RepositoryState
from engine.core.models.position import Position
from engine.core.state.repository_state import GP_CAP


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
    def from_new_game(cls, manifest: dict, protagonist_name: str, scenario_path: Path | None = None) -> "GameState":
        """
        Bootstrap a fresh game state from manifest + player-entered name.
        """
        state = cls()

        # flags
        bootstrap_flags = manifest.get("bootstrap_flags", [])
        state.flags.add_flags(bootstrap_flags)

        # protagonist
        proto = manifest.get("protagonist", {})
        char_data = {}
        if scenario_path:
            char_file = proto.get("character")
            if char_file:
                char_path = scenario_path / char_file
                if char_path.exists():
                    with open(char_path, "r") as f:
                        char_data = yaml.safe_load(f) or {}
        member = MemberState(
            member_id=proto.get("id", "protagonist"),
            name=protagonist_name,
            protagonist=True,
            class_name=char_data["class"],
            level=char_data["level"],
            exp=char_data["exp"],
            hp=char_data["hp"],
            hp_max=char_data["hp_max"],
            mp=char_data["mp"],
            mp_max=char_data["mp_max"],
            str_=char_data["str"],
            dex=char_data["dex"],
            con=char_data["con"],
            int_=char_data["int"],
            equipped=char_data["equipped"],
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
                member_id=m["id"],
                name=m["name"],
                protagonist=m["protagonist"],
                class_name=m.get("class", ""),
                level=m.get("level", 1),
                exp=m["exp"],
                hp=m["hp"],
                hp_max=m["hp_max"],
                mp=m["mp"],
                mp_max=m["mp_max"],
                str_=m["str"],
                dex=m["dex"],
                con=m["con"],
                int_=m["int"],
                equipped=m.get("equipped", {}),
            ))
        repo = save.get("party_repository", {})
        state.repository._gp = min(repo.get("gp", 0), GP_CAP)
        for item in repo.get("items", []):
            state.repository.add_item(item["id"], item["qty"])
            entry = state.repository.get_item(item["id"])
            entry.tags = set(item.get("tags", []))
            entry.locked = item.get("locked", False)
        return state

    def __repr__(self) -> str:
        return (
            f"GameState("
            f"flags={len(self.flags.to_list())}, "
            f"map={self.map.current!r}, "
            f"playtime={self.playtime.display})"
        )