# tests/unit/core/equipment/test_starting_equipment.py
#
# Scenario integration: every character's starting `equipped:` block must
# reference items in the real ItemCatalog AND be equippable by that class.
# Guards against character/item catalog drift.

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from engine.item.item_catalog import ItemCatalog
from engine.party.member_state import MemberState
from engine.equipment.equipment_logic import can_equip


SCENARIO = Path("rusted_kingdoms")


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def catalog() -> ItemCatalog:
    if not (SCENARIO / "data" / "items").is_dir():
        pytest.skip("Scenario data not available")
    return ItemCatalog(SCENARIO / "data" / "items")


@pytest.fixture(scope="module")
def characters() -> list[tuple[str, dict, dict]]:
    """List of (char_id, entry, class_data) for each party member.

    Loads from the merged data/party.yaml — see engine/party/party_data.py.
    The entry dict is flattened so callers can read cd['hp'], cd['equipped'],
    cd['str'] etc. (stats are nested under 'stats:' in the YAML).
    """
    party_path = SCENARIO / "data" / "party.yaml"
    class_dir = SCENARIO / "data" / "classes"
    if not party_path.is_file() or not class_dir.is_dir():
        pytest.skip("Scenario data not available")
    out = []
    party_data = _load_yaml(party_path)
    for entry in party_data["party"]:
        cd = dict(entry)
        cd.update(entry["stats"])  # flatten str/dex/con/int for legacy assertions
        cls = _load_yaml(class_dir / f"{entry['class']}.yaml")
        out.append((entry["id"], cd, cls))
    return out


class TestStartingEquipmentValid:
    def test_every_slot_value_is_string(self, characters):
        for char_id, cd, _ in characters:
            for slot, val in cd.get("equipped", {}).items():
                assert isinstance(val, str), \
                    f"{char_id}.equipped[{slot}] must be a string, got {type(val).__name__}"

    def test_every_equipped_item_exists_in_catalog(self, catalog, characters):
        for char_id, cd, _ in characters:
            for slot, item_id in cd.get("equipped", {}).items():
                if not item_id:
                    continue
                assert item_id in catalog, \
                    f"{char_id}.equipped[{slot}] = {item_id!r} not in catalog"

    def test_every_equipped_item_matches_slot_type(self, catalog, characters):
        for char_id, cd, _ in characters:
            for slot, item_id in cd.get("equipped", {}).items():
                if not item_id:
                    continue
                defn = catalog.get(item_id)
                assert defn.type == slot, (
                    f"{char_id}.equipped[{slot}] = {item_id!r} "
                    f"has type={defn.type!r}, expected {slot!r}"
                )

    def test_every_equipped_item_passes_can_equip(self, catalog, characters):
        for char_id, cd, cls in characters:
            member = MemberState(
                member_id=cd["id"], name=cd["name"],
                protagonist=cd.get("protagonist", False),
                class_name=cd["class"], level=cd["level"], exp=cd["exp"],
                hp=cd["hp"], hp_max=cd["hp_max"],
                mp=cd["mp"], mp_max=cd["mp_max"],
                str_=cd["str"], dex=cd["dex"], con=cd["con"], int_=cd["int"],
                equipped=cd.get("equipped", {}),
            )
            member.load_class_data(cls)
            for slot, item_id in member.equipped.items():
                if not item_id:
                    continue
                defn = catalog.get(item_id)
                assert can_equip(member, defn), (
                    f"{char_id} ({cd['class']}) cannot equip {item_id!r} "
                    f"in slot {slot!r} — class rules reject it"
                )


class TestRoundTrip:
    def test_equipped_survives_save_serialization(self, catalog, characters):
        from engine.common.game_state import GameState
        from engine.io.save_manager import GameStateManager, AUTOSAVE_INDEX

        _, cd, cls = characters[0]   # aric
        state = GameState()
        state.repository.catalog = catalog
        member = MemberState(
            member_id=cd["id"], name=cd["name"],
            protagonist=True, class_name=cd["class"],
            level=cd["level"], exp=cd["exp"],
            hp=cd["hp"], hp_max=cd["hp_max"],
            mp=cd["mp"], mp_max=cd["mp_max"],
            str_=cd["str"], dex=cd["dex"], con=cd["con"], int_=cd["int"],
            equipped=dict(cd.get("equipped", {})),
        )
        member.load_class_data(cls)
        state.party.add_member(member)

        serialized = GameStateManager(
            saves_dir="/tmp/not_used",
            classes_dir=SCENARIO / "data" / "classes",
            item_catalog=catalog,
        )._serialize(state, is_autosave=True)

        saved_equipped = serialized["party"][0]["equipped"]
        assert saved_equipped == cd["equipped"]
