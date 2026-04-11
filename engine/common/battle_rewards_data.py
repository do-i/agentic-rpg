# engine/dto/battle_rewards.py

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
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


@dataclass
class MemberExpResult:
    member_id:   str
    member_name: str
    exp_gained:  int
    level_ups:   list[LevelUpResult] = field(default_factory=list)


@dataclass
class LootResult:
    mc_drops:   list[dict] = field(default_factory=list)   # [{"size": "S", "qty": 1}, ...]
    item_drops: list[dict] = field(default_factory=list)   # [{"id": "rat_tail", "name": "Rat Tail", "qty": 1}, ...]
    gp_gained:  int = 0


@dataclass
class BattleRewards:
    total_exp:      int
    member_results: list[MemberExpResult]
    loot:           LootResult
    boss_flag:      str = ""
