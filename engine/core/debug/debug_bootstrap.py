# engine/core/debug/debug_bootstrap.py
#
# Debug only — adds all party members to GameState at new game start.
# Enabled via engine/config/settings.yaml:
#   debug:
#     party: true

from __future__ import annotations
from pathlib import Path
import yaml

from engine.core.state.game_state import GameState
from engine.core.state.party_state import MemberState


def inject_full_party(state: GameState, scenario_path: Path) -> None:
    """
    Reads data/party.yaml and data/characters/*.yaml from the scenario,
    adds all non-protagonist members to GameState with their starting stats.
    Safe to call even if party.yaml is missing — silently no-ops.
    """
    party_path = scenario_path / "data" / "party.yaml"
    if not party_path.exists():
        print("[DEBUG] party.yaml not found — skipping debug party inject")
        return

    with open(party_path, "r") as f:
        data = yaml.safe_load(f) or {}

    existing_ids = {m.id for m in state.party.members}

    for entry in data.get("party", []):
        member_id = entry.get("id")
        if not member_id or member_id in existing_ids:
            continue

        # load character YAML for starting stats
        char_file = entry.get("character")
        char_data = {}
        if char_file:
            char_path = scenario_path / char_file
            if char_path.exists():
                with open(char_path, "r") as f:
                    char_data = yaml.safe_load(f) or {}

        member = MemberState(
            member_id=member_id,
            name=char_data.get("name", entry.get("name", member_id)),
            protagonist=False,
            class_name=char_data.get("class", entry.get("class", "")),
            level=char_data.get("level", 1),
            exp=char_data.get("exp", 0),
            exp_next=100,
            hp=char_data.get("hp", 20),
            hp_max=char_data.get("hp_max", char_data.get("hp", 20)),
            mp=char_data.get("mp", 0),
            mp_max=char_data.get("mp_max", char_data.get("mp", 0)),
            str_=char_data.get("str", 10),
            dex=char_data.get("dex", 10),
            con=char_data.get("con", 10),
            int_=char_data.get("int", 10),
            equipped=char_data.get("equipped", {}),
        )
        state.party.add_member(member)
        print(f"[DEBUG] added party member: {member.name} ({member.class_name})")
