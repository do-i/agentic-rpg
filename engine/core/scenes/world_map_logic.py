# engine/core/scenes/world_map_logic.py
#
# World map logic — interaction, encounters, portals, transitions.
# Extracted from world_map_scene.py to separate game logic from scene wiring.

from __future__ import annotations

import yaml
from pathlib import Path

from engine.core.models.position import Position
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.state.game_state_manager import GameStateManager
from engine.core.dialogue.dialogue_engine import DialogueEngine
from engine.core.encounter.encounter_manager import EncounterManager
from engine.world.npc import Npc
from engine.world.player import Player, COLLISION_W, COLLISION_H
from engine.world.sprite_sheet import Direction
from engine.world.tile_map import TileMap

FADE_SPEED = 300

# Direction → unit vector for "player is facing toward NPC" check.
_DIR_DX = {Direction.LEFT: -1, Direction.RIGHT: 1, Direction.UP: 0, Direction.DOWN: 0}
_DIR_DY = {Direction.UP: -1, Direction.DOWN: 1, Direction.LEFT: 0, Direction.RIGHT: 0}


def _is_player_facing(player: Player, npc_pos) -> bool:
    """True if the NPC is roughly in the direction the player faces."""
    pp = player.pixel_position
    dx = npc_pos.x - pp.x
    dy = npc_pos.y - pp.y
    facing = player.facing_direction
    return dx * _DIR_DX[facing] + dy * _DIR_DY[facing] > 0


def try_interact(player: Player, npcs: list[Npc], flags, dialogue_engine: DialogueEngine):
    """Try to interact with a nearby NPC. Returns (dialogue_result, npc) or (None, None).

    When multiple NPCs are in range, picks the closest one.
    Ties are broken by whether the player is facing the NPC.
    """
    if player is None:
        return None, None
    player_pos = player.pixel_position

    # Collect all nearby, present NPCs.
    candidates: list[Npc] = []
    for npc in npcs:
        if npc.is_present(flags) and npc.is_near(player_pos):
            candidates.append(npc)

    if not candidates:
        return None, None

    # Sort: closest first, then prefer NPC the player is facing.
    def _sort_key(npc: Npc):
        np = npc.pixel_position
        dist_sq = (np.x - player_pos.x) ** 2 + (np.y - player_pos.y) ** 2
        facing = 0 if _is_player_facing(player, np) else 1
        return (dist_sq, facing)

    candidates.sort(key=_sort_key)

    for npc in candidates:
        result = dialogue_engine.resolve(npc.dialogue_id, flags)
        if result:
            return result, npc
    return None, None


def dispatch_dialogue_result(on_complete: dict, flags, repository, dialogue_engine: DialogueEngine) -> dict:
    """Process on_complete dict from dialogue. Returns remaining actions."""
    if not on_complete:
        return {}
    return dialogue_engine.dispatch_on_complete(on_complete, flags, repository)


def check_encounter(holder: GameStateHolder, encounter_manager: EncounterManager,
                    player: Player):
    """Check for a random encounter on the current tile.
    Returns (battle_state, boss_flag) or (None, "").
    """
    state = holder.get()
    inventory_ids: set[str] = {
        entry.id for entry in state.repository.items
    }
    battle_state = encounter_manager.on_step(
        flags=state.flags,
        party=state.party,
        inventory_item_ids=inventory_ids,
    )
    if battle_state is None:
        return None, ""

    boss_flag = getattr(battle_state, "boss_flag", "")
    state.map.set_position(player.tile_position)
    return battle_state, boss_flag


def check_portals(tile_map: TileMap, player: Player) -> dict | None:
    """Check if player is on a portal. Returns transition dict or None."""
    if tile_map is None or player is None:
        return None
    col = player.collision_rect_position
    for portal in tile_map.portals:
        if portal.is_triggered_by(col.x, col.y, COLLISION_W, COLLISION_H):
            return {
                "map": portal.target_map,
                "position": [portal.target_position.x, portal.target_position.y],
            }
    return None


def apply_transition(holder: GameStateHolder, game_state_manager: GameStateManager,
                     player: Player, transition: dict) -> None:
    """Save state and update map position for a transition."""
    state = holder.get()
    state.map.set_position(player.tile_position)
    game_state_manager.save(state, slot_index=0)

    new_map = transition.get("map", state.map.current)
    pos = transition.get("position", [0, 0])
    state.map.move_to(new_map, Position.from_list(pos))


def load_inn_cost(scenario_path: Path, map_id: str) -> int:
    """Load inn cost from map YAML data."""
    map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
    with open(map_yaml) as f:
        map_data = yaml.safe_load(f)
    return map_data.get("inn", {}).get("cost", 50)


def load_shop_items(scenario_path: Path, map_id: str) -> list[dict]:
    """Load shop items from map YAML data."""
    map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
    with open(map_yaml) as f:
        map_data = yaml.safe_load(f)
    return map_data.get("shop", {}).get("items", [])


def load_magic_cores(scenario_path: Path) -> list[dict]:
    """Load magic core definitions from scenario item data.

    Returns list of dicts with keys: id, name, exchange_rate.
    Ordered by exchange_rate descending (XL first).
    """
    mc_path = scenario_path / "data" / "items" / "magic_cores.yaml"
    if not mc_path.exists():
        return []
    with open(mc_path) as f:
        items = yaml.safe_load(f) or []
    return sorted(items, key=lambda d: d.get("exchange_rate", 0), reverse=True)
