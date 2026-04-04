# tests/unit/core/scenes/test_world_map_logic.py

import pytest
from unittest.mock import MagicMock, PropertyMock, patch
from pathlib import Path

from engine.core.models.position import Position
from engine.core.scenes.world_map_logic import (
    try_interact, dispatch_dialogue_result,
    check_encounter, check_portals, apply_transition,
    load_inn_cost, load_shop_items,
)


# ── try_interact ──────────────────────────────────────────────

class TestTryInteract:
    def test_returns_none_when_no_player(self):
        result, npc = try_interact(None, [], MagicMock(), MagicMock())
        assert result is None
        assert npc is None

    def test_returns_none_when_no_npcs_nearby(self):
        player = MagicMock()
        player.pixel_position = MagicMock()
        npc = MagicMock()
        npc.is_present.return_value = True
        npc.is_near.return_value = False

        result, found = try_interact(player, [npc], MagicMock(), MagicMock())
        assert result is None

    def test_returns_dialogue_when_npc_near(self):
        player = MagicMock()
        player.pixel_position = MagicMock()
        npc = MagicMock()
        npc.is_present.return_value = True
        npc.is_near.return_value = True
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
        player.pixel_position = MagicMock()
        hidden = MagicMock()
        hidden.is_present.return_value = False

        result, _ = try_interact(player, [hidden], MagicMock(), MagicMock())
        assert result is None


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


# ── check_encounter ───────────────────────────────────────────

class TestCheckEncounter:
    def test_no_encounter(self):
        holder = MagicMock()
        state = MagicMock()
        state.repository.items = []
        holder.get.return_value = state

        em = MagicMock()
        em.on_step.return_value = None

        player = MagicMock()

        battle, flag = check_encounter(holder, em, player)
        assert battle is None
        assert flag == ""

    def test_encounter_triggered(self):
        holder = MagicMock()
        state = MagicMock()
        state.repository.items = []
        holder.get.return_value = state

        battle_state = MagicMock()
        battle_state.boss_flag = "boss_1"

        em = MagicMock()
        em.on_step.return_value = battle_state

        player = MagicMock()
        player.tile_position = Position(5, 3)

        battle, flag = check_encounter(holder, em, player)
        assert battle is battle_state
        assert flag == "boss_1"
        state.map.set_position.assert_called_with(Position(5, 3))


# ── check_portals ─────────────────────────────────────────────

class TestCheckPortals:
    def test_none_when_no_map(self):
        assert check_portals(None, MagicMock()) is None

    def test_none_when_no_player(self):
        assert check_portals(MagicMock(), None) is None

    def test_returns_transition_on_trigger(self):
        player = MagicMock()
        player.collision_rect_position = MagicMock(x=100, y=200)

        portal = MagicMock()
        portal.is_triggered_by.return_value = True
        portal.target_map = "dungeon_01"
        portal.target_position = MagicMock(x=5, y=3)

        tile_map = MagicMock()
        tile_map.portals = [portal]

        result = check_portals(tile_map, player)

        assert result == {"map": "dungeon_01", "position": [5, 3]}

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
    def test_saves_and_moves(self):
        holder = MagicMock()
        state = MagicMock()
        state.map.current = "town_01"
        holder.get.return_value = state

        gsm = MagicMock()
        player = MagicMock()
        player.tile_position = Position(3, 4)

        transition = {"map": "dungeon_01", "position": [10, 20]}

        apply_transition(holder, gsm, player, transition)

        state.map.set_position.assert_called_with(Position(3, 4))
        gsm.save.assert_called_once_with(state, slot_index=0)
        state.map.move_to.assert_called_once()


# ── load_inn_cost / load_shop_items ───────────────────────────

class TestLoadMapData:
    def test_load_inn_cost(self, tmp_path):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "town_01.yaml").write_text("inn:\n  cost: 75\n")

        cost = load_inn_cost(tmp_path, "town_01")
        assert cost == 75

    def test_load_inn_cost_default(self, tmp_path):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "town_01.yaml").write_text("npcs: []\n")

        cost = load_inn_cost(tmp_path, "town_01")
        assert cost == 50

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
