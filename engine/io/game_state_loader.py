# engine/io/game_state_loader.py
#
# Factory functions for creating GameState from new-game manifest or save data.

from __future__ import annotations
from pathlib import Path
import yaml

from engine.common.game_state import GameState
from engine.common.flag_state import FlagState
from engine.common.map_state import MapState
from engine.common.opened_boxes_state import OpenedBoxesState
from engine.party.member_state import MemberState
from engine.world.position_data import Position
from engine.party.party_state import calc_exp_next
from engine.util.playtime import Playtime

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.item.item_catalog import ItemCatalog


def _load_class_data(classes_dir: Path, class_name: str) -> dict:
    path = classes_dir / f"{class_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Class YAML not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _load_character_data(scenario_path: Path, char_path_str: str) -> dict:
    path = scenario_path / char_path_str
    if not path.exists():
        raise FileNotFoundError(f"Character YAML not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def from_new_game(
    manifest: dict,
    protagonist_name: str,
    classes_dir: Path,
    scenario_path: Path,
    item_catalog: ItemCatalog | None = None,
) -> GameState:
    state = GameState()
    state.repository.catalog = item_catalog

    bootstrap_flags = manifest.get("bootstrap_flags", [])
    state.flags.add_flags(bootstrap_flags)

    proto      = manifest["protagonist"]
    class_name = proto["class"]
    class_data = _load_class_data(classes_dir, class_name)
    char_data  = _load_character_data(scenario_path, proto["character"])

    member = MemberState(
        member_id=proto["id"],
        name=protagonist_name,
        protagonist=True,
        class_name=class_name,
        level=1,
        exp=0,
        hp=char_data["hp_max"],
        hp_max=char_data["hp_max"],
        mp=char_data["mp_max"],
        mp_max=char_data["mp_max"],
        str_=char_data["str"],
        dex=char_data["dex"],
        con=char_data["con"],
        int_=char_data["int"],
        equipped=char_data.get("equipped", {}),
    )
    member.load_class_data(class_data)
    member.exp_next = calc_exp_next(member, member.level)
    state.party.add_member(member)

    start = manifest["start"]
    state.map.move_to(
        map_id=start["map"],
        position=Position.from_list(start["position"]),
    )

    state.playtime.start_session()
    return state


def from_save(
    save: dict,
    classes_dir: Path,
    item_catalog: ItemCatalog | None = None,
) -> GameState:
    state = GameState()
    state.repository.catalog = item_catalog
    state.flags        = FlagState.from_set(set(save["flags"]))
    state.map          = MapState.from_dict(save["map"])
    state.opened_boxes = OpenedBoxesState.from_list(save.get("opened_boxes", []))
    state.playtime     = Playtime.from_seconds(save["meta"]["playtime_seconds"])
    state.playtime.start_session()

    # -- Party --
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
        member.load_class_data(class_data)
        exp_next = m.get("exp_next")
        member.exp_next = exp_next if exp_next is not None else calc_exp_next(member, member.level)
        state.party.add_member(member)

    # -- Repository — GP + items --
    repo_data = save.get("party_repository", {})
    gp = repo_data.get("gp", 0)
    state.repository.add_gp(gp)

    for item in repo_data.get("items", []):
        item_id = item.get("id")
        qty     = item.get("qty", 1)
        tags    = set(item.get("tags", []))
        locked  = item.get("locked", False)
        if item_id:
            entry = state.repository.add_item(item_id, qty)
            entry.tags   = tags
            entry.locked = locked
            if item_id.startswith("mc_"):
                entry.tags.add("magic_core")

    return state
