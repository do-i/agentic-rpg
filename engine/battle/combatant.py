# engine/battle/combatant.py
#
# Phase 4 — Battle system

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from engine.util.pseudo_random import PseudoRandom


class StatusEffect(Enum):
    POISON    = auto()
    SLEEP     = auto()
    STUN      = auto()
    SILENCE   = auto()
    BURN      = auto()
    FREEZE    = auto()
    KNOCKBACK = auto()


@dataclass
class ActiveStatus:
    """One status effect applied to a combatant with per-tick state.

    `damage_per_turn` — burn DOT resolved at application time.
    `atk_modifier`   — knockback multiplier on source ATK (e.g. 0.80).
    """
    effect:          StatusEffect
    duration_turns:  int
    damage_per_turn: int = 0
    atk_modifier:    float = 1.0


# Effects that prevent the combatant from acting on their turn.
SKIP_TURN_EFFECTS = (StatusEffect.STUN, StatusEffect.FREEZE, StatusEffect.SLEEP)


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
    # Row only applies to party members. Enemies leave it as "front"; the
    # row math in action_resolver only triggers when row == "back".
    row:       str = "front"
    portrait_path: str = ""     # party members only — assets/images/{id}_profile.png
    sprite_id: str = ""         # enemies — placeholder label for now
    sprite_scale: int = 100     # enemies — enlarge sprite by this %, 100 = no change

    # battle-only state
    status_effects: list[ActiveStatus] = field(default_factory=list)
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

    @property
    def effective_atk(self) -> int:
        """ATK after applying all active knockback modifiers."""
        mult = 1.0
        for s in self.status_effects:
            if s.effect is StatusEffect.KNOCKBACK:
                mult *= s.atk_modifier
        return max(1, int(self.atk * mult))

    @property
    def is_silenced(self) -> bool:
        return self.has_status(StatusEffect.SILENCE)

    @property
    def skip_turn_reason(self) -> StatusEffect | None:
        for s in self.status_effects:
            if s.effect in SKIP_TURN_EFFECTS:
                return s.effect
        return None

    def apply_damage(self, amount: int, rng: PseudoRandom) -> int:
        """Clamps to 0, sets KO flag. Returns actual damage dealt.

        If the combatant is defending, damage is reduced by 25-30%.
        """
        if self.defending:
            reduction = rng.uniform(0.25, 0.30)
            amount = max(1, int(amount * (1 - reduction)))
        # actual = displayed damage (capped at remaining HP); self.hp uses the
        # raw amount but is floored at 0, so the returned value can be < amount
        # even though hp ends up at 0. Keep both clamps — they protect against
        # negative-amount bugs from upstream regressions.
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
        return any(s.effect is effect for s in self.status_effects)

    def add_status(self, active_status: ActiveStatus) -> None:
        """Apply a status. If the same effect is already present, refresh it
        (replace duration and modifiers — does not stack)."""
        for i, s in enumerate(self.status_effects):
            if s.effect is active_status.effect:
                self.status_effects[i] = active_status
                return
        self.status_effects.append(active_status)

    def remove_status(self, effect: StatusEffect) -> None:
        self.status_effects = [s for s in self.status_effects if s.effect is not effect]

    def clear_all_status(self) -> None:
        self.status_effects.clear()

    def tick_end_of_turn(self) -> int:
        """Called at the end of this combatant's turn.

        Applies burn DOT to self and decrements all status durations. Removes
        expired statuses. Returns the total DOT damage inflicted this tick
        (caller renders the float / KO check).
        """
        dot_damage = 0
        for s in self.status_effects:
            if s.effect is StatusEffect.BURN and s.damage_per_turn > 0:
                dot_damage += s.damage_per_turn

        if dot_damage > 0:
            actual = min(dot_damage, self.hp)
            self.hp = max(0, self.hp - dot_damage)
            if self.hp == 0:
                self.is_ko = True
            dot_damage = actual

        # Decrement and filter in a single pass to avoid iterating
        # self.status_effects while it's about to be replaced.
        remaining: list[ActiveStatus] = []
        for s in self.status_effects:
            s.duration_turns -= 1
            if s.duration_turns > 0:
                remaining.append(s)
        self.status_effects = remaining
        return dot_damage

    def __repr__(self) -> str:
        tag = "[KO]" if self.is_ko else f"HP{self.hp}/{self.hp_max}"
        return f"Combatant({self.name!r}, {tag})"
