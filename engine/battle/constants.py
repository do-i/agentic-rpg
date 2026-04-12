# engine/battle/constants.py
#
# Shared layout constants for the battle system.
# Used by both battle_logic.py (float positioning) and battle_renderer.py (drawing).


# ── Layout ────────────────────────────────────────────────────
ENEMY_AREA_H = 468
ROW_H = 56

ENEMY_LAYOUTS = {
    1: [(0,   0)],
    2: [(-80, 0),  (80,  0)],
    3: [(-110, -30), (0, 20), (110, -20)],
    4: [(-140, -20), (-45, 20), (45, -20), (140, 20)],
    5: [(-160, -30), (-80, 20), (0, -10), (80, 20), (160, -30)],
}

ENEMY_SIZES = {
    "boss":   (96, 96),
    "large":  (80, 80),
    "medium": (64, 64),
    "small":  (52, 52),
}
