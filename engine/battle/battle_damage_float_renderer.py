# engine/battle/battle_damage_float_renderer.py
#
# Renders the floating damage/heal numbers that drift up and fade out over
# every hit. Caches the (shadow, foreground) pair per DamageFloat instance
# so the per-frame work is just a set_alpha and two blits.

from __future__ import annotations

import pygame

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_state import BattleState


class DamageFloatRenderer:
    def __init__(self, assets: BattleAssetCache) -> None:
        self._assets = assets
        # Damage-float text + shadow surfaces, keyed by id(DamageFloat).
        self._cache: dict[int, tuple[pygame.Surface, pygame.Surface]] = {}

    def draw(self, screen: pygame.Surface, state: BattleState) -> None:
        live_ids: set[int] = set()
        for f in state.damage_floats:
            key = id(f)
            live_ids.add(key)
            pair = self._cache.get(key)
            if pair is None:
                shadow = self._assets.font_dmg.render(f.text, True, (0, 0, 0))
                surf = self._assets.font_dmg.render(f.text, True, f.color)
                pair = (shadow, surf)
                self._cache[key] = pair
            shadow, surf = pair
            shadow.set_alpha(f.alpha)
            for ox, oy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2)):
                screen.blit(shadow, (f.x + ox, f.y + oy))
            surf.set_alpha(f.alpha)
            screen.blit(surf, (f.x, f.y))
        # Drop entries for floats that have expired and were pruned by the
        # state. id() is only safe to compare against live objects, so we
        # filter against this frame's set.
        if len(self._cache) != len(live_ids):
            for k in list(self._cache.keys()):
                if k not in live_ids:
                    del self._cache[k]
