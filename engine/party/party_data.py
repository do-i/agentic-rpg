# engine/party/party_data.py
#
# Single helper for reading the scenario's merged party.yaml — used by every
# code path that materializes a MemberState from scenario data:
#   - engine/io/game_state_loader.py     (from_new_game protagonist)
#   - engine/world/world_map_logic.py    (apply_join_party companion)
#   - engine/debug/debug_bootstrap.py    (inject_full_party debug mode)
#   - engine/battle/battle_asset_cache.py (load_portrait)

from __future__ import annotations

from pathlib import Path

from engine.io.yaml_loader import load_yaml_required_cached
from engine.party.member_state import MemberState
from engine.party.party_state import calc_exp_next


_VALID_ROWS = ("front", "back")


def party_yaml_path(scenario_path: Path) -> Path:
    return scenario_path / "data" / "party.yaml"


def load_party_entries(scenario_path: Path) -> list[dict]:
    """Return the full list of party entries from data/party.yaml."""
    data = load_yaml_required_cached(party_yaml_path(scenario_path))
    entries = data["party"]
    if not isinstance(entries, list):
        raise ValueError(
            f"{party_yaml_path(scenario_path)}: 'party' must be a list. "
            f"Example:\n  party:\n    - id: aric\n      ..."
        )
    return entries


def load_party_entry(scenario_path: Path, member_id: str) -> dict:
    """Return one party entry by id. Raises ValueError if not found."""
    for entry in load_party_entries(scenario_path):
        if entry["id"] == member_id:
            return entry
    raise ValueError(
        f"party.yaml has no entry with id={member_id!r}. "
        f"Available: {[e['id'] for e in load_party_entries(scenario_path)]}"
    )


def build_member(entry: dict, class_data: dict, *, name_override: str | None = None) -> MemberState:
    """Construct a MemberState from a party.yaml entry + its class YAML.

    name_override is used by from_new_game when the player has typed a custom
    protagonist name on the name-entry screen.
    """
    stats = entry["stats"]
    row = entry["row"]
    if row not in _VALID_ROWS:
        raise ValueError(
            f"party.yaml entry {entry['id']!r}: row must be one of {_VALID_ROWS}, "
            f"got {row!r}. Example:\n  row: back"
        )

    member = MemberState(
        member_id=entry["id"],
        name=name_override if name_override is not None else entry["name"],
        protagonist=entry["protagonist"],
        class_name=entry["class"],
        level=entry["level"],
        exp=entry["exp"],
        hp=entry["hp"],
        hp_max=entry["hp_max"],
        mp=entry["mp"],
        mp_max=entry["mp_max"],
        str_=stats["str"],
        dex=stats["dex"],
        con=stats["con"],
        int_=stats["int"],
        equipped=dict(entry["equipped"]),
    )
    member.load_class_data(class_data)
    member.row = row  # entry wins over class default_row
    member.exp_next = calc_exp_next(member, member.level)
    return member


def recruit_block(entry: dict) -> dict | None:
    """Return entry['recruit'] (npc/dialogue/joined_flag) or None for protagonist."""
    return entry.get("recruit")
