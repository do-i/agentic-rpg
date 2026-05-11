# engine/debug/debug_bootstrap.py
#
# Debug only — adds all party members to GameState at new game start.
# Enabled via engine/settings/settings.yaml:
#   debug:
#     party: true

from __future__ import annotations
from pathlib import Path

from engine.common.game_state import GameState
from engine.io.yaml_loader import load_yaml_required_cached
from engine.party.party_data import build_member, load_party_entries, recruit_block


def inject_full_party(state: GameState, scenario_path: Path) -> None:
    existing_ids = {m.id for m in state.party.members}

    for entry in load_party_entries(scenario_path):
        if entry["id"] in existing_ids:
            continue

        class_data = load_yaml_required_cached(
            scenario_path / "data" / "classes" / f"{entry['class']}.yaml"
        )
        state.party.add_member(build_member(entry, class_data))

        # Auto-set the recruit's joined_flag so its overworld NPC despawns
        # — without this, debug-mode recruits walk around their towns as
        # "ghosts" until you re-trigger their join dialogue.
        recruit = recruit_block(entry)
        if recruit:
            state.flags.add_flag(recruit["joined_flag"])
