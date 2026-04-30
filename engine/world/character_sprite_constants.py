# engine/world/character_sprite_constants.py
#
# Shared sprite / collision / animation constants for on-map characters
# (player, NPCs, enemy sprites). Identical footprint convention keeps the
# three sprite renderers in lockstep so they can collide with each other.

# Render — square sprite in pixels
from __future__ import annotations

CHAR_SPRITE_SIZE = 64

# Collision rect — smaller than sprite; centered horizontally, feet-aligned
COLLISION_W = 20
COLLISION_H = 18
COLLISION_OFFSET_X = (CHAR_SPRITE_SIZE - COLLISION_W) // 2       # 22
COLLISION_OFFSET_Y = CHAR_SPRITE_SIZE - COLLISION_H - 5          # 41

# Animation frames (9-frame row: idle + 8 walk frames)
IDLE_FRAME     = 0
WALK_START     = 1
WALK_END       = 8
BASE_FRAME_DUR = 0.15   # seconds per frame at speed 1.0

# Wander timing
WANDER_PAUSE_MIN = 1.0   # seconds between moves
WANDER_PAUSE_MAX = 3.5
