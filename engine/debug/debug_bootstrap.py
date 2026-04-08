# engine/debug/debug_bootstrap.py
#
# Debug only — adds all party members to GameState at new game start.
# Enabled via engine/config/settings.yaml:
#   debug:
#     party: true

from __future__ import annotations
from pathlib import Path
import yaml

from engine.dto.game_state import GameState
from engine.dto.member_state import MemberState
from engine.service.party_state import calc_exp_next


def _load_class_data(scenario_path: Path, class_name: str) -> dict:
    path = scenario_path / "data" / "classes" / f"{class_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Class YAML not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def inject_full_party(state: GameState, scenario_path: Path) -> None:
    party_path = scenario_path / "data" / "party.yaml"
    if not party_path.exists():
        raise FileNotFoundError(f"party.yaml not found: {party_path}")

    with open(party_path, "r") as f:
        data = yaml.safe_load(f)

    existing_ids = {m.id for m in state.party.members}

    for entry in data["party"]:
        member_id = entry["id"]
        if member_id in existing_ids:
            continue

        char_path = scenario_path / entry["character"]
        if not char_path.exists():
            raise FileNotFoundError(f"Character YAML not found: {char_path}")
        with open(char_path, "r") as f:
            char_data = yaml.safe_load(f)

        class_name = char_data["class"]
        class_data = _load_class_data(scenario_path, class_name)

        member = MemberState(
            member_id=member_id,
            name=char_data["name"],
            protagonist=False,
            class_name=class_name,
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
            exp_next=calc_exp_next(class_name, char_data["level"]),
        )
        member.load_stat_growth(class_data)
        state.party.add_member(member)
        print(f"[DEBUG] added: {member.name} ({class_name}) "
              f"Lv{member.level} exp_next={member.exp_next}")
