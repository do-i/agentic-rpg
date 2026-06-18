# engine/dto/battle_rewards.py

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LevelUpResult:
    member_id:   str
    member_name: str
    old_level:   int
    new_level:   int
    hp_gained:   int
    mp_gained:   int
    str_gained:  int
    dex_gained:  int
    con_gained:  int
    int_gained:  int
    # Post-growth absolute totals — drive the before -> after columns in the
    # level-up modal. "before" is recovered as total - gained.
    hp_max:      int
    mp_max:      int
    str_total:   int
    dex_total:   int
    con_total:   int
    int_total:   int


@dataclass(frozen=True)
class MemberExpResult:
    member_id:   str
    member_name: str
    exp_gained:  int
    level_ups:   list[LevelUpResult] = field(default_factory=list)


@dataclass(frozen=True)
class LootResult:
    mc_drops:   list[dict] = field(default_factory=list)   # [{"size": "S", "qty": 1}, ...]
    item_drops: list[dict] = field(default_factory=list)   # [{"id": "rat_tail", "name": "Rat Tail", "qty": 1}, ...]
    gp_gained:  int = 0


@dataclass(frozen=True)
class BattleRewards:
    total_exp:      int
    member_results: list[MemberExpResult]
    loot:           LootResult
    boss_flag:      str = ""
