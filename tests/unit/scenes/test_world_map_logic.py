# tests/unit/core/scenes/test_world_map_logic.py

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock, patch
from pathlib import Path

from engine.world.position_data import Position
from engine.world.world_map_logic import (
    try_interact, dispatch_dialogue_result,
    apply_join_party,
    check_portals, apply_transition,
    load_inn_cost, load_shop_items, load_recipes,
)
from engine.world.sprite_sheet import Direction
from engine.party.party_state import PartyState


# ── try_interact ──────────────────────────────────────────────

class TestTryInteract:
    def test_returns_none_when_no_player(self):
        result, npc = try_interact(None, [], MagicMock(), MagicMock())
        assert result is None
        assert npc is None

    def test_returns_none_when_no_npcs_nearby(self):
        player = MagicMock()
        player.pixel_position = Position(100, 100)
        player.facing_direction = Direction.DOWN
        npc = MagicMock()
        npc.is_present.return_value = True
        npc.is_near.return_value = False

        result, found = try_interact(player, [npc], MagicMock(), MagicMock())
        assert result is None

    def test_returns_dialogue_when_npc_near(self):
        player = MagicMock()
        player.pixel_position = Position(100, 100)
        player.facing_direction = Direction.DOWN
        npc = MagicMock()
        npc.is_present.return_value = True
        npc.is_near.return_value = True
        npc.pixel_position = Position(100, 132)
        npc.dialogue_id = "merchant_01"

        dialogue_engine = MagicMock()
        dialogue_engine.resolve.return_value = {"lines": ["Hello!"]}
        flags = MagicMock()

        result, found_npc = try_interact(player, [npc], flags, dialogue_engine)

        assert result == {"lines": ["Hello!"]}
        assert found_npc is npc
        dialogue_engine.resolve.assert_called_with("merchant_01", flags)

    def test_skips_hidden_npcs(self):
        player = MagicMock()
        player.pixel_position = Position(100, 100)
        player.facing_direction = Direction.DOWN
        hidden = MagicMock()
        hidden.is_present.return_value = False

        result, _ = try_interact(player, [hidden], MagicMock(), MagicMock())
        assert result is None

    def test_selects_closest_npc_when_multiple_nearby(self):
        player = MagicMock()
        player.pixel_position = Position(100, 100)
        player.facing_direction = Direction.DOWN

        far_npc = MagicMock()
        far_npc.is_present.return_value = True
        far_npc.is_near.return_value = True
        far_npc.pixel_position = Position(140, 100)
        far_npc.dialogue_id = "far_npc"

        close_npc = MagicMock()
        close_npc.is_present.return_value = True
        close_npc.is_near.return_value = True
        close_npc.pixel_position = Position(110, 100)
        close_npc.dialogue_id = "close_npc"

        dialogue_engine = MagicMock()
        dialogue_engine.resolve.return_value = {"lines": ["Hi!"]}
        flags = MagicMock()

        # far_npc is first in list, but close_npc should be selected
        result, found_npc = try_interact(player, [far_npc, close_npc], flags, dialogue_engine)

        assert found_npc is close_npc
        dialogue_engine.resolve.assert_called_with("close_npc", flags)

    def test_facing_breaks_distance_tie(self):
        player = MagicMock()
        player.pixel_position = Position(100, 100)
        player.facing_direction = Direction.RIGHT

        # Both NPCs are equidistant
        npc_left = MagicMock()
        npc_left.is_present.return_value = True
        npc_left.is_near.return_value = True
        npc_left.pixel_position = Position(80, 100)  # to the left
        npc_left.dialogue_id = "left"

        npc_right = MagicMock()
        npc_right.is_present.return_value = True
        npc_right.is_near.return_value = True
        npc_right.pixel_position = Position(120, 100)  # to the right
        npc_right.dialogue_id = "right"

        dialogue_engine = MagicMock()
        dialogue_engine.resolve.return_value = {"lines": ["Hi!"]}
        flags = MagicMock()

        # Player faces right, so npc_right should win the tie
        result, found_npc = try_interact(player, [npc_left, npc_right], flags, dialogue_engine)

        assert found_npc is npc_right


# ── dispatch_dialogue_result ──────────────────────────────────

class TestDispatchDialogueResult:
    def test_empty_on_complete(self):
        result = dispatch_dialogue_result({}, MagicMock(), MagicMock(), MagicMock())
        assert result == {}

    def test_none_on_complete(self):
        result = dispatch_dialogue_result(None, MagicMock(), MagicMock(), MagicMock())
        assert result == {}

    def test_delegates_to_engine(self):
        engine = MagicMock()
        engine.dispatch_on_complete.return_value = {"open_shop": "item"}

        result = dispatch_dialogue_result(
            {"some": "data"}, "flags", "repo", engine,
        )

        assert result == {"open_shop": "item"}
        engine.dispatch_on_complete.assert_called_with({"some": "data"}, "flags", "repo")


# ── apply_join_party ──────────────────────────────────────────

class TestApplyJoinParty:
    def test_adds_missing_companion(self, tmp_path):
        _write_join_fixture(tmp_path, "elise", class_name="cleric", row="back")
        party = PartyState()

        added = apply_join_party(tmp_path, party, "elise")

        assert added is True
        assert [m.id for m in party.members] == ["elise"]
        assert party.members[0].row == "back"
        assert party.members[0].exp_next > 0

    def test_skips_existing_companion(self, tmp_path):
        _write_join_fixture(tmp_path, "elise", class_name="cleric", row="back")
        party = PartyState()

        assert apply_join_party(tmp_path, party, "elise") is True
        assert apply_join_party(tmp_path, party, "elise") is False

        assert [m.id for m in party.members] == ["elise"]


def _write_join_fixture(tmp_path: Path, member_id: str, class_name: str, row: str) -> None:
    from engine.io.yaml_loader import clear_yaml_cache

    data_dir = tmp_path / "data"
    class_dir = data_dir / "classes"
    data_dir.mkdir(parents=True, exist_ok=True)
    class_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "party.yaml").write_text(
        f"""
party:
  - id: {member_id}
    name: Elise
    class: {class_name}
    protagonist: false
    row: {row}
    level: 1
    exp: 0
    hp: 18
    hp_max: 18
    mp: 18
    mp_max: 18
    stats: {{ str: 8, dex: 9, con: 10, int: 11 }}
    equipped: {{}}
""".lstrip()
    )
    (class_dir / f"{class_name}.yaml").write_text(
        """
default_row: back
exp_base: 95
exp_factor: 2.0
stat_growth:
  str: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
  dex: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
  con: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
  int: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
equipment_slots: {}
""".lstrip()
    )
    # party.yaml is cached by path — clear so each tmp_path test reads its own.
    clear_yaml_cache()


# ── check_portals ─────────────────────────────────────────────

class TestCheckPortals:
    def test_none_when_no_map(self):
        assert check_portals(None, MagicMock()) is None

    def test_none_when_no_player(self):
        assert check_portals(MagicMock(), None) is None

    def test_returns_transition_on_trigger(self):
        player = MagicMock()
        player.collision_rect_position = MagicMock(x=100, y=200)
        player.facing_direction = Direction.UP

        portal = MagicMock()
        portal.is_triggered_by.return_value = True
        portal.target_map = "dungeon_01"
        portal.target_position = MagicMock(x=5, y=3)

        tile_map = MagicMock()
        tile_map.portals = [portal]

        result = check_portals(tile_map, player)

        assert result == {
            "map": "dungeon_01", "position": [5, 3], "facing": int(Direction.UP),
        }

    def test_returns_none_when_not_triggered(self):
        player = MagicMock()
        player.collision_rect_position = MagicMock(x=100, y=200)

        portal = MagicMock()
        portal.is_triggered_by.return_value = False

        tile_map = MagicMock()
        tile_map.portals = [portal]

        result = check_portals(tile_map, player)
        assert result is None


# ── apply_transition ──────────────────────────────────────────

class TestApplyTransition:
    def test_moves_then_saves(self):
        """Move first, then autosave — so the saved state reflects the
        destination map/position, not the portal-trigger tile on the old map."""
        holder = MagicMock()
        state = MagicMock()
        state.map.current = "town_01"
        holder.get.return_value = state

        gsm = MagicMock()
        player = MagicMock()
        player.tile_position = Position(3, 4)

        transition = {"map": "dungeon_01", "position": [10, 20],
                      "facing": int(Direction.UP)}

        # save must come after move_to so the snapshot lands at the destination.
        manager = MagicMock()
        manager.attach_mock(state.map.move_to, "move_to")
        manager.attach_mock(gsm.save, "save")

        apply_transition(holder, gsm, player, transition)

        state.map.move_to.assert_called_once_with(
            "dungeon_01", Position(10, 20), Direction.UP,
        )
        gsm.save.assert_called_once_with(state, slot_index=0)
        ordered = [name for name, *_ in manager.mock_calls]
        assert ordered.index("move_to") < ordered.index("save")

    def test_skips_save_on_same_map(self):
        """Intra-map portal (target == current) should move but not autosave."""
        holder = MagicMock()
        state = MagicMock()
        state.map.current = "town_01"
        holder.get.return_value = state

        gsm = MagicMock()
        player = MagicMock()
        player.tile_position = Position(0, 0)

        apply_transition(holder, gsm, player, {"map": "town_01", "position": [5, 6],
                                               "facing": int(Direction.LEFT)})

        state.map.move_to.assert_called_once_with("town_01", Position(5, 6), Direction.LEFT)
        gsm.save.assert_not_called()

    def test_missing_map_raises(self):
        holder = MagicMock()
        gsm = MagicMock()
        player = MagicMock()
        player.tile_position = Position(0, 0)

        with pytest.raises(KeyError, match="'map'"):
            apply_transition(holder, gsm, player, {"position": [0, 0]})

    def test_missing_position_raises(self):
        holder = MagicMock()
        gsm = MagicMock()
        player = MagicMock()
        player.tile_position = Position(0, 0)

        with pytest.raises(KeyError, match="'position'"):
            apply_transition(holder, gsm, player, {"map": "town_01"})

    def test_missing_facing_raises(self):
        holder = MagicMock()
        gsm = MagicMock()
        player = MagicMock()
        player.tile_position = Position(0, 0)

        with pytest.raises(KeyError, match="'facing'"):
            apply_transition(holder, gsm, player, {"map": "town_01", "position": [0, 0]})


# ── load_inn_cost / load_shop_items ───────────────────────────

class TestLoadMapData:
    def test_load_inn_cost(self, tmp_path):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "town_01.yaml").write_text("inn:\n  cost: 75\n")

        cost = load_inn_cost(tmp_path, "town_01")
        assert cost == 75

    def test_load_inn_cost_missing_raises(self, tmp_path):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "town_01.yaml").write_text("npcs: []\n")

        with pytest.raises(KeyError, match="inn.cost"):
            load_inn_cost(tmp_path, "town_01")

    def test_load_shop_items(self, tmp_path):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "town_01.yaml").write_text(
            "shop:\n  items:\n    - id: potion\n      buy_price: 50\n"
        )

        items = load_shop_items(tmp_path, "town_01")
        assert len(items) == 1
        assert items[0]["id"] == "potion"

    def test_load_shop_items_empty(self, tmp_path):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "town_01.yaml").write_text("npcs: []\n")

        items = load_shop_items(tmp_path, "town_01")
        assert items == []


# ── load_recipes ──────────────────────────────────────────────

class TestLoadRecipes:
    def test_returns_empty_list_when_file_missing(self, tmp_path):
        result = load_recipes(tmp_path)
        assert result == []

    def test_loads_recipes_from_yaml(self, tmp_path):
        recipe_dir = tmp_path / "data" / "recipe"
        recipe_dir.mkdir(parents=True)
        content = "- id: antidote\n  ingredients: [herb]\n"
        (recipe_dir / "all_recipe.yaml").write_text(content)
        result = load_recipes(tmp_path)
        assert len(result) == 1
        assert result[0]["id"] == "antidote"


# ── try_interact — no dialogue result ─────────────────────────

class TestTryInteractNoResult:
    def test_returns_none_when_all_npcs_have_no_dialogue(self):
        player = MagicMock()
        player.pixel_position = Position(100, 100)
        player.facing_direction = Direction.DOWN

        npc = MagicMock()
        npc.is_present.return_value = True
        npc.is_near.return_value = True
        npc.pixel_position = Position(100, 132)
        npc.dialogue_id = "empty_npc"

        dialogue_engine = MagicMock()
        dialogue_engine.resolve.return_value = None  # no dialogue resolves

        result, found = try_interact(player, [npc], MagicMock(), dialogue_engine)
        assert result is None
        assert found is None
