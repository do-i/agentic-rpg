# engine/world/world_map_logic.py
#
# World map logic — interaction, encounters, portals, transitions.
# Extracted from world_map_scene.py to separate game logic from scene wiring.

from __future__ import annotations

from pathlib import Path

from engine.io.yaml_loader import load_yaml_optional, load_yaml_required
from engine.world.position_data import Position
from engine.common.game_state_holder import GameStateHolder
from engine.io.save_manager import GameStateManager
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.world.item_box import ItemBox
from engine.world.npc import Npc
from engine.world.player import Player, COLLISION_W, COLLISION_H
from engine.world.sprite_sheet import Direction
from engine.world.tile_map import TileMap

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


def apply_item_box_loot(box: ItemBox, repository, opened_boxes, map_id: str) -> None:
    """Transfer a chest's contents into the party repository and mark it opened."""
    for item_id, qty in box.loot_items:
        repository.add_item(item_id, qty)
    for mc_id, qty in box.loot_magic_cores:
        entry = repository.add_item(mc_id, qty)
        entry.tags.add("magic_core")
    opened_boxes.mark_opened(map_id, box.id)


def try_interact_item_box(
    player: Player,
    item_boxes: list[ItemBox],
    flags,
    opened_boxes,
    map_id: str,
) -> ItemBox | None:
    """Return the nearest present, unopened ItemBox the player is facing, or None."""
    if player is None:
        return None
    player_pos = player.pixel_position

    candidates: list[ItemBox] = []
    for box in item_boxes:
        if not box.is_present(flags):
            continue
        if opened_boxes.is_opened(map_id, box.id):
            continue
        if not box.is_near(player_pos):
            continue
        if not _is_player_facing(player, box.pixel_position):
            continue
        candidates.append(box)

    if not candidates:
        return None

    def _dist_sq(b: ItemBox) -> int:
        bp = b.pixel_position
        return (bp.x - player_pos.x) ** 2 + (bp.y - player_pos.y) ** 2

    candidates.sort(key=_dist_sq)
    return candidates[0]


def dispatch_dialogue_result(on_complete: dict, flags, repository, dialogue_engine: DialogueEngine) -> dict:
    """Process on_complete dict from dialogue. Returns remaining actions."""
    if not on_complete:
        return {}
    return dialogue_engine.dispatch_on_complete(on_complete, flags, repository)


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
    """Update map position for a transition; autosave only when the map id changes.

    Skipping the autosave on intra-map portals avoids redundant full YAML writes
    for teleports that don't represent meaningful progression.
    """
    if "position" not in transition:
        raise KeyError(f"transition missing required field 'position': {transition!r}")
    if "map" not in transition:
        raise KeyError(f"transition missing required field 'map': {transition!r}")
    state = holder.get()
    target_map = transition["map"]
    map_changed = target_map != state.map.current
    state.map.move_to(target_map, Position.from_list(transition["position"]))
    if map_changed:
        game_state_manager.save(state, slot_index=0)


def load_inn_cost(scenario_path: Path, map_id: str) -> int:
    """Load inn cost from map YAML data."""
    map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
    map_data = load_yaml_required(map_yaml)
    inn = map_data.get("inn") or {}
    if "cost" not in inn:
        raise KeyError(f"{map_id}.yaml: inn.cost is required")
    return inn["cost"]


def load_shop_items(scenario_path: Path, map_id: str) -> list[dict]:
    """Load shop items from map YAML data."""
    map_yaml = scenario_path / "data" / "maps" / f"{map_id}.yaml"
    map_data = load_yaml_required(map_yaml)
    return map_data.get("shop", {}).get("items", [])


def load_recipes(scenario_path: Path) -> list[dict]:
    """Load apothecary recipes from scenario data."""
    recipe_path = scenario_path / "data" / "recipe" / "all_recipe.yaml"
    return load_yaml_optional(recipe_path) or []


def load_magic_cores(scenario_path: Path) -> list[dict]:
    """Load magic core definitions from scenario item data.

    Returns list of dicts with keys: id, name, exchange_rate.
    Ordered by exchange_rate descending (XL first).
    """
    mc_path = scenario_path / "data" / "items" / "magic_cores.yaml"
    items = load_yaml_optional(mc_path) or []
    return sorted(items, key=lambda d: d["exchange_rate"], reverse=True)
