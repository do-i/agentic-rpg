# engine/world/npc_loader.py

from pathlib import Path
import yaml

from engine.world.npc import Npc


class NpcLoader:
    """
    Reads NPC entries from a map YAML file and returns Npc instances.
    Handles both town NPCs and world map gate NPCs.
    """

    def load_from_map(self, map_yaml_path: Path) -> list[Npc]:
        if not map_yaml_path.exists():
            return []

        with open(map_yaml_path, "r") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            return []

        return [self._parse_npc(entry) for entry in data.get("npcs", [])]

    def _parse_npc(self, entry: dict) -> Npc:
        npc_id    = entry.get("id", "unknown")
        dialogue  = entry.get("dialogue", npc_id)
        position  = entry.get("position", [0, 0])
        present   = entry.get("present", {}) or {}

        return Npc(
            npc_id=npc_id,
            dialogue_id=dialogue,
            tile_x=position[0],
            tile_y=position[1],
            present_requires=present.get("requires", []),
            present_excludes=present.get("excludes", []),
        )
