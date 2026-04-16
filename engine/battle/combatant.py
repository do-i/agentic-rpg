# engine/battle/combatant.py
#
# Phase 4 — Battle system

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from engine.util.pseudo_random import PseudoRandom


class StatusEffect(Enum):
    POISON  = auto()
    SLEEP   = auto()
    STUN    = auto()
    SILENCE = auto()


@dataclass
class Combatant:
    """
    Runtime battle state for one party member or enemy.
    Constructed from character YAML / enemy YAML at battle start.
    """
    id:        str
    name:      str
    hp:        int
    hp_max:    int
    mp:        int
    mp_max:    int
    atk:       int
    def_:      int
    mres:      int
    dex:       int
    is_enemy:  bool = False
    boss:      bool = False
    portrait_path: str = ""     # party members only — assets/images/{id}_profile.png
    sprite_id: str = ""         # enemies — placeholder label for now
    sprite_scale: int = 100     # enemies — enlarge sprite by this %, 100 = no change

    # battle-only state
    status_effects: list[StatusEffect] = field(default_factory=list)
    is_ko:     bool = False
    defending: bool = False

    # reward stats — enemies only
    exp_yield: int = 0

    # abilities available this battle — list of ability dicts from class YAML
    abilities: list[dict] = field(default_factory=list)

    # drop table from enemy YAML — {mc: [...], loot: [...]}
    drops: dict = field(default_factory=dict)

    # AI data from enemy YAML — {ai: {pattern, moves}, targeting: {default, overrides}}
    ai_data: dict = field(default_factory=dict)

    @property
    def hp_pct(self) -> float:
        return self.hp / self.hp_max if self.hp_max > 0 else 0.0

    @property
    def is_alive(self) -> bool:
        return not self.is_ko and self.hp > 0

    def apply_damage(self, amount: int, rng: PseudoRandom) -> int:
        """Clamps to 0, sets KO flag. Returns actual damage dealt.

        If the combatant is defending, damage is reduced by 25-30%.
        """
        if self.defending:
            reduction = rng.uniform(0.25, 0.30)
            amount = max(1, int(amount * (1 - reduction)))
        actual = min(amount, self.hp)
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.is_ko = True
        return actual

    def apply_heal(self, amount: int) -> int:
        """Returns actual HP restored."""
        if self.is_ko:
            return 0
        before = self.hp
        self.hp = min(self.hp_max, self.hp + amount)
        return self.hp - before

    def has_status(self, effect: StatusEffect) -> bool:
        return effect in self.status_effects

    def add_status(self, effect: StatusEffect) -> None:
        if effect not in self.status_effects:
            self.status_effects.append(effect)

    def remove_status(self, effect: StatusEffect) -> None:
        if effect in self.status_effects:
            self.status_effects.remove(effect)

    def clear_all_status(self) -> None:
        self.status_effects.clear()

    def __repr__(self) -> str:
        tag = "[KO]" if self.is_ko else f"HP{self.hp}/{self.hp_max}"
        return f"Combatant({self.name!r}, {tag})"
