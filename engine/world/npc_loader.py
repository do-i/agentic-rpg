# engine/io/npc_loader.py

from pathlib import Path
import yaml

from engine.world.npc import Npc
from engine.world.sprite_sheet import SpriteSheet
from engine.util.pseudo_random import PseudoRandom


class NpcLoader:
    """
    Reads NPC entries from a map YAML file and returns Npc instances.
    Handles both town NPCs and world map gate NPCs.
    Loads sprite sheet from TSX path if provided.
    """

    def __init__(self, tile_size: int, scenario_path: Path | None = None, rng: PseudoRandom | None = None) -> None:
        self._scenario_path = scenario_path
        self._tile_size = tile_size
        self._rng = rng

    def load_from_map(self, map_yaml_path: Path) -> list[Npc]:
        if not map_yaml_path.exists():
            return []

        with open(map_yaml_path, "r") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            return []

        return [self._parse_npc(entry) for entry in data.get("npcs", [])]

    def _parse_npc(self, entry: dict) -> Npc:
        for key in ("id", "position"):
            if key not in entry:
                raise KeyError(f"npc entry missing required field {key!r}: {entry!r}")
        npc_id         = entry["id"]
        dialogue       = entry.get("dialogue", npc_id)
        position       = entry["position"]
        present        = entry.get("present", {}) or {}
        default_facing = entry.get("default_facing", "down")
        sprite_tsx     = entry.get("sprite")

        anim           = entry.get("animation", {}) or {}
        anim_mode      = anim.get("mode", "still")
        anim_speed     = anim.get("speed", 1.0)
        wander_range   = anim.get("range", 2)
        interaction_range_tiles = entry.get("interaction_range", 1.5)

        sprite_sheet = self._load_sprite(sprite_tsx) if sprite_tsx else None

        return Npc(
            npc_id=npc_id,
            dialogue_id=dialogue,
            tile_x=position[0],
            tile_y=position[1],
            present_requires=present.get("requires", []),
            present_excludes=present.get("excludes", []),
            sprite_sheet=sprite_sheet,
            default_facing=default_facing,
            anim_mode=anim_mode,
            anim_speed=anim_speed,
            wander_range=wander_range,
            interaction_range_tiles=interaction_range_tiles,
            tile_size=self._tile_size,
            rng=self._rng,
        )

    def _load_sprite(self, sprite_path: str) -> SpriteSheet | None:
        if self._scenario_path is None:
            return None
        full_path = self._scenario_path / sprite_path
        if not full_path.exists():
            print(f"[WARN] NPC sprite not found: {full_path}")
            return None
        try:
            return SpriteSheet(full_path)
        except Exception as e:
            print(f"[WARN] Failed to load NPC sprite {full_path}: {e}")
            return None
