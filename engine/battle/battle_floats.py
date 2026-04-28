# engine/battle/battle_floats.py
#
# Shared damage-float positioning and color palette for the battle system.
# Lives in its own module so action_resolver and turn_advance can both
# import the helpers without re-importing battle_logic (which would loop).

from __future__ import annotations

from engine.battle.battle_state import BattleState
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H, ENEMY_LAYOUTS, ENEMY_SIZES, ROW_H


# ── Float colors ──────────────────────────────────────────────
C_DMG_PHYS  = (255, 180, 80)
C_DMG_MAGIC = (140, 180, 255)
C_HEAL      = (100, 220, 100)
C_DEFEND    = (180, 180, 255)


def enemy_rect_size(enemy: Combatant) -> tuple[int, int]:
    if enemy.boss:
        return ENEMY_SIZES["large"]
    idx = len(enemy.name) % 3
    return [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]


def float_pos(state: BattleState, combatant: Combatant,
              screen_width: int) -> tuple[int, int]:
    """Screen position for a damage float over the given combatant."""
    if combatant.is_enemy:
        n = len(state.enemies)
        idx = state.enemies.index(combatant)
        ox, oy = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])[idx]
        cx = screen_width // 2 + ox
        cy = ENEMY_AREA_H // 2 + 10 + oy
        _, h = enemy_rect_size(combatant)
        return cx - 15, cy - h // 2 - 30
    else:
        idx = state.party.index(combatant)
        party_w = screen_width // 2
        return party_w - 60, ENEMY_AREA_H + 8 + idx * (ROW_H + 2) + 5
