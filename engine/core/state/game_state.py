# engine/core/state/game_state.py

from __future__ import annotations
from pathlib import Path
import yaml

from engine.core.state.flag_state import FlagState
from engine.core.state.map_state import MapState
from engine.core.state.playtime import Playtime
from engine.core.state.party_state import PartyState, MemberState
from engine.core.state.repository_state import RepositoryState
from engine.core.models.position import Position


def _load_class_data(classes_dir: Path, class_name: str) -> dict:
    path = classes_dir / f"{class_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Class YAML not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


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
    def from_new_game(
        cls,
        manifest: dict,
        protagonist_name: str,
        classes_dir: Path,
    ) -> "GameState":
        state = cls()

        bootstrap_flags = manifest.get("bootstrap_flags", [])
        state.flags.add_flags(bootstrap_flags)

        proto      = manifest["protagonist"]
        class_name = proto["class"]
        class_data = _load_class_data(classes_dir, class_name)

        member = MemberState(
            member_id=proto["id"],
            name=protagonist_name,
            protagonist=True,
            class_name=class_name,
            level=1,
            exp=0,
            hp=class_data["base_hp"],
            hp_max=class_data["base_hp"],
            mp=class_data["base_mp"],
            mp_max=class_data["base_mp"],
            str_=class_data["stat_growth"]["str"][0],
            dex=class_data["stat_growth"]["dex"][0],
            con=class_data["stat_growth"]["con"][0],
            int_=class_data["stat_growth"]["int"][0],
            equipped={},
        )
        member.load_stat_growth(class_data)
        state.party.add_member(member)

        start = manifest["start"]
        state.map.move_to(
            map_id=start["map"],
            position=Position.from_list(start["position"]),
        )

        state.playtime.start_session()
        return state

    # ── Factory: Load Game ────────────────────────────────────

    @classmethod
    def from_save(cls, save: dict, classes_dir: Path) -> "GameState":
        state = cls()
        state.flags    = FlagState.from_set(set(save["flags"]))
        state.map      = MapState.from_dict(save["map"])
        state.playtime = Playtime.from_seconds(save["meta"]["playtime_seconds"])
        state.playtime.start_session()

        for m in save["party"]:
            class_name = m["class"]
            class_data = _load_class_data(classes_dir, class_name)

            member = MemberState(
                member_id=m["id"],
                name=m["name"],
                protagonist=m["protagonist"],
                class_name=class_name,
                level=m["level"],
                exp=m["exp"],
                exp_next=m.get("exp_next"),   # None → auto-calculated
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
            member.load_stat_growth(class_data)
            state.party.add_member(member)

        return state

    def __repr__(self) -> str:
        return (
            f"GameState("
            f"flags={len(self.flags.to_list())}, "
            f"map={self.map.current!r}, "
            f"playtime={self.playtime.display})"
        )
