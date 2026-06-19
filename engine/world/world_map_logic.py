# engine/world/world_map_logic.py
#
# World map logic — interaction, encounters, portals, transitions.
# Extracted from world_map_scene.py to separate game logic from scene wiring.

from __future__ import annotations

from pathlib import Path

from engine.io.yaml_loader import load_yaml_optional, load_yaml_required, load_yaml_required_cached
from engine.world.position_data import Position
from engine.common.game_state_holder import GameStateHolder
from engine.io.save_manager import GameStateManager
from engine.dialogue.dialogue_engine import DialogueEngine
from engine.party.member_state import MemberState
from engine.party.party_data import build_member, load_party_entry
from engine.party.party_state import calc_exp_next
from engine.world.item_box import ItemBox
from engine.world.npc import Npc
from engine.world.sign import Sign
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


def try_interact_sign(player: Player, signs: list[Sign], flags, dialogue_engine: DialogueEngine):
    """Read the nearest sign the player is facing. Returns a DialogueResult or None.

    Mirrors item-box interaction: only the sign directly in front of the player
    is read, and the closest one wins when several are in range.
    """
    if player is None:
        return None
    player_pos = player.pixel_position

    candidates: list[Sign] = []
    for sign in signs:
        if sign.is_near(player_pos) and _is_player_facing(player, sign.pixel_position):
            candidates.append(sign)

    if not candidates:
        return None

    def _dist_sq(s: Sign) -> int:
        sp = s.pixel_position
        return (sp.x - player_pos.x) ** 2 + (sp.y - player_pos.y) ** 2

    candidates.sort(key=_dist_sq)

    for sign in candidates:
        result = dialogue_engine.resolve(sign.dialogue_id, flags)
        if result:
            return result
    return None


def apply_item_box_loot(box: ItemBox, repository, opened_boxes, map_id: str) -> None:
    """Transfer a chest's contents into the party repository and mark it opened."""
    # One chest = one loot batch shared by all its contents.
    batch = repository.start_loot_batch()
    for item_id, qty in box.loot_items:
        entry = repository.add_item(item_id, qty)
        entry.is_loot = True
        entry.loot_batch = batch
    for mc_id, qty in box.loot_magic_cores:
        entry = repository.add_item(mc_id, qty)
        entry.tags.add("magic_core")
        entry.is_loot = True
        entry.loot_batch = batch
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


def apply_join_party(scenario_path: Path, party, member_id: str) -> bool:
    """Load and add a companion by id. Returns True when a member was added."""
    if not member_id:
        return False
    if any(member.id == member_id for member in party.members):
        return False

    entry = load_party_entry(scenario_path, member_id)
    class_data = load_yaml_required_cached(
        scenario_path / "data" / "classes" / f"{entry['class']}.yaml"
    )
    party.add_member(build_member(entry, class_data))
    return True


# How far (in tiles) the player's facing border may be before we assume they
# arrived through it and would otherwise spawn staring back off the map. Landing
# tiles sit 1-2 tiles inside an edge; anything deeper is a normal inward arrival.
_OFF_MAP_FACING_MARGIN = 2

# Distance from a tile to the map border in the direction the player faces.
_DIST_TO_FACED_BORDER = {
    Direction.UP:    lambda x, y, w, h: y,
    Direction.DOWN:  lambda x, y, w, h: (h - 1) - y,
    Direction.LEFT:  lambda x, y, w, h: x,
    Direction.RIGHT: lambda x, y, w, h: (w - 1) - x,
}
_OPPOSITE_FACING = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


def face_into_map(
    facing: Direction, tile_x: int, tile_y: int, map_w: int, map_h: int
) -> Direction:
    """Correct arrival facing so the player never spawns staring off the map.

    Most map links connect opposite edges (exit south -> enter the north edge),
    so the travel direction already points *into* the destination and is kept
    unchanged. But some links connect the *same* compass edge of both maps
    (the world layout is a graph, not a coherent grid): there, arriving with the
    travel facing leaves the player at the edge they entered, looking back out
    of it. Detect that by checking the border the player faces — only when it is
    right in front of them (within a couple tiles) do we flip the facing inward.
    A mid-map arrival, or one already facing inward, is left untouched.

    Purely a sprite-orientation fix: it never moves the player, so it cannot push
    them into a wall.
    """
    dist = _DIST_TO_FACED_BORDER[facing](tile_x, tile_y, map_w, map_h)
    if dist <= _OFF_MAP_FACING_MARGIN:
        return _OPPOSITE_FACING[facing]
    return facing


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
                # Carry the direction of travel so the player arrives facing
                # the way they walked (away from the entrance), not always south.
                "facing": int(player.facing_direction),
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
    if "facing" not in transition:
        raise KeyError(f"transition missing required field 'facing': {transition!r}")
    state = holder.get()
    target_map = transition["map"]
    map_changed = target_map != state.map.current
    state.map.move_to(
        target_map,
        Position.from_list(transition["position"]),
        Direction(transition["facing"]),
    )
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
