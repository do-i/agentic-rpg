# engine/shop/shop_constants.py
#
# Shared colors and layout constants used by all shop scenes.

from __future__ import annotations

from engine.common.ui.theme import BORDER, DIM, EMBER, GOLD, INK, MUTED

# ── Colors (shared across shops — field-menu theme) ──────────
C_BG       = (16, 16, 20)
C_TEXT     = INK
C_MUTED    = MUTED
C_DIM      = DIM
C_GP       = GOLD
C_NORM_BDR = BORDER
C_ROW_BG   = (30, 30, 38)
C_DIVIDER  = BORDER
C_HINT     = DIM
C_WARN     = EMBER
C_TOAST    = (132, 196, 111)
C_LOCKED   = DIM

# ── Layout (shared across shops) ─────────────────────────────
MODAL_W  = 560
HEADER_H = 48
ROW_GAP  = 4
