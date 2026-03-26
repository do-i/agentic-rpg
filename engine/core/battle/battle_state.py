# engine/core/battle/battle_state.py
#
# Phase 4 — Battle system

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from engine.core.battle.combatant import Combatant


class BattlePhase(Enum):
    PLAYER_TURN    = auto()   # waiting for player input
    SELECT_SPELL   = auto()   # spell submenu open
    SELECT_ITEM    = auto()   # item submenu open
    SELECT_TARGET  = auto()   # player chose action, picking target
    RESOLVE        = auto()   # animation + damage playing out
    ENEMY_TURN     = auto()   # enemy AI resolving
    CHECK_RESULT   = auto()   # win / lose check
    POST_BATTLE    = auto()   # exp + loot screen  # stub — Phase 4
    GAME_OVER      = auto()


@dataclass
class DamageFloat:
    """Floating damage number rendered over enemy/party."""
    text:    str
    x:       int
    y:       int
    color:   tuple        # RGB
    alpha:   int  = 255
    vy:      float = -40.0   # pixels/sec upward drift

    def update(self, delta: float) -> None:
        self.y += int(self.vy * delta)
        self.alpha = max(0, self.alpha - int(300 * delta))

    @property
    def expired(self) -> bool:
        return self.alpha <= 0


@dataclass
class BattleState:
    """
    Full runtime state for one battle encounter.
    Created by BattleScene at encounter trigger.
    """
    party:   list[Combatant]          # up to 5 party members, in display order
    enemies: list[Combatant]          # 1–5 enemies

    phase:         BattlePhase = BattlePhase.PLAYER_TURN
    active_index:  int = 0            # index into turn_order
    turn_order:    list[Combatant] = field(default_factory=list)

    # pending action — set during SELECT_* phases, consumed in RESOLVE
    pending_action:  dict | None = None   # {type, ability_id, source, targets}

    # visual feedback
    damage_floats: list[DamageFloat] = field(default_factory=list)
    message:       str = ""               # bottom message text

    # boss metadata — set by EncounterManager when a boss battle is triggered
    boss_flag:     str = ""               # flag to set on victory

    def build_turn_order(self) -> None:
        """Sort all alive combatants by DEX descending. Party wins ties."""
        alive = [c for c in self.party + self.enemies if c.is_alive]
        self.turn_order = sorted(alive, key=lambda c: (c.dex, not c.is_enemy), reverse=True)
        self.active_index = 0

    @property
    def active(self) -> Combatant | None:
        if not self.turn_order:
            return None
        if self.active_index >= len(self.turn_order):
            return None
        return self.turn_order[self.active_index]

    def advance_turn(self) -> None:
        """Move to next alive combatant in turn order."""
        for _ in range(len(self.turn_order)):
            self.active_index = (self.active_index + 1) % len(self.turn_order)
            if self.turn_order[self.active_index].is_alive:
                return

    def add_float(self, text: str, x: int, y: int, color: tuple) -> None:
        self.damage_floats.append(DamageFloat(text, x, y, color))

    def update_floats(self, delta: float) -> None:
        for f in self.damage_floats:
            f.update(delta)
        self.damage_floats = [f for f in self.damage_floats if not f.expired]

    @property
    def party_wiped(self) -> bool:
        return all(not c.is_alive for c in self.party)

    @property
    def enemies_wiped(self) -> bool:
        return all(not c.is_alive for c in self.enemies)

    def alive_enemies(self) -> list[Combatant]:
        return [e for e in self.enemies if e.is_alive]

    def alive_party(self) -> list[Combatant]:
        return [p for p in self.party if p.is_alive]
