# engine/battle/battle_renderer_constants.py
#
# Colors and layout constants specific to battle rendering.
# Shared battle layout (ENEMY_AREA_H, ENEMY_LAYOUTS, etc.) lives in constants.py.

from __future__ import annotations

from engine.battle.combatant import StatusEffect

# ── Layout ────────────────────────────────────────────────────
PORTRAIT_SIZE = 36
ROW_PAD       = 8
BAR_H         = 6

# ── Status effect badge colors ────────────────────────────────
STATUS_COLORS = {
    StatusEffect.POISON:    ((51, 102, 51),  (170, 255, 170), "PSN"),
    StatusEffect.SLEEP:     ((68, 68, 170),  (204, 204, 255), "zzz"),
    StatusEffect.STUN:      ((120, 90, 20),  (255, 220, 100), "STN"),
    StatusEffect.SILENCE:   ((100, 60, 100), (220, 180, 220), "SIL"),
    StatusEffect.BURN:      ((140, 40, 40),  (255, 170, 120), "BRN"),
    StatusEffect.FREEZE:    ((40, 80, 140),  (180, 220, 255), "FRZ"),
    StatusEffect.KNOCKBACK: ((90, 90, 120),  (210, 210, 230), "KBK"),
}

# ── Colors ────────────────────────────────────────────────────
C_FLOOR        = (17,  17,  40)
C_PANEL_LINE   = (51,  51,  51)
C_ROW_ACTIVE   = (42,  26,  26)
C_ROW_NORMAL   = (26,  26,  42)
C_BORDER_ACT   = (255, 220, 60)
C_BORDER_NORM  = (51,  51,  68)
C_CMD_SEL_BG   = (42,  32,  64)
C_CMD_SEL_BDR  = (119, 85,  204)
C_HP_OK        = (68,  170, 68)
C_HP_LOW       = (204, 68,  68)
C_MP           = (68,  102, 204)
C_HP_LABEL_OK  = (136, 204, 136)
C_HP_LABEL_LOW = (204, 136, 136)
C_MP_LABEL     = (136, 136, 204)
C_MSG_ENEMY    = (255, 170, 50)
C_MSG_PARTY    = (100, 200, 255)
