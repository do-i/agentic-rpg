# engine/settings/balance_data.py
#
# Scenario balance constants (level caps, economy caps, combat/spawner
# tunables, movement speed). Loaded once from the scenario's balance.yaml.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class BalanceData:
    # progression
    level_cap: int
    exp_cap:   int
    # economy
    gp_cap:            int
    item_qty_cap:      int
    max_tags_per_item: int
    # battle
    flee_base_chance:     float
    flee_rogue_dex_bonus: float
    # spawner
    rogue_chase_reduction:    int
    stealth_cloak_reduction:  int
    lure_charm_interval_mult: float
    # movement
    player_speed: int

    @classmethod
    def load(cls, scenario_path: Path, manifest: dict) -> "BalanceData":
        rel = (manifest.get("refs") or {}).get("balance")
        if not rel:
            raise KeyError(
                f"manifest.yaml is missing refs.balance pointing to a balance YAML file "
                f"(scenario: {scenario_path})"
            )
        path = scenario_path / rel
        if not path.exists():
            raise FileNotFoundError(f"balance file not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        prog  = data.get("progression") or {}
        econ  = data.get("economy")     or {}
        batt  = data.get("battle")      or {}
        spawn = data.get("spawner")     or {}
        move  = data.get("movement")    or {}

        required = {
            "progression.level_cap":          prog.get("level_cap"),
            "progression.exp_cap":            prog.get("exp_cap"),
            "economy.gp_cap":                 econ.get("gp_cap"),
            "economy.item_qty_cap":           econ.get("item_qty_cap"),
            "economy.max_tags_per_item":      econ.get("max_tags_per_item"),
            "battle.flee_base_chance":        batt.get("flee_base_chance"),
            "battle.flee_rogue_dex_bonus":    batt.get("flee_rogue_dex_bonus"),
            "spawner.rogue_chase_reduction":  spawn.get("rogue_chase_reduction"),
            "spawner.stealth_cloak_reduction": spawn.get("stealth_cloak_reduction"),
            "spawner.lure_charm_interval_mult": spawn.get("lure_charm_interval_mult"),
            "movement.player_speed":          move.get("player_speed"),
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise KeyError(f"balance YAML missing required keys: {', '.join(missing)}")

        return cls(
            level_cap=int(required["progression.level_cap"]),
            exp_cap=int(required["progression.exp_cap"]),
            gp_cap=int(required["economy.gp_cap"]),
            item_qty_cap=int(required["economy.item_qty_cap"]),
            max_tags_per_item=int(required["economy.max_tags_per_item"]),
            flee_base_chance=float(required["battle.flee_base_chance"]),
            flee_rogue_dex_bonus=float(required["battle.flee_rogue_dex_bonus"]),
            rogue_chase_reduction=int(required["spawner.rogue_chase_reduction"]),
            stealth_cloak_reduction=int(required["spawner.stealth_cloak_reduction"]),
            lure_charm_interval_mult=float(required["spawner.lure_charm_interval_mult"]),
            player_speed=int(required["movement.player_speed"]),
        )
