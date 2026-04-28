# engine/battle/battle_hit_flash.py
#
# Shared additive-flash overlay used by both the enemy-area and party-panel
# renderers. Caches per-(w, h) Surface for the non-sprite branch so the
# generic rectangle flash doesn't allocate every frame.

from __future__ import annotations

import pygame

from engine.battle.battle_fx import BattleFx
from engine.battle.combatant import Combatant


class HitFlash:
    """Renders the additive flash overlay. The cache is per-instance — both
    EnemyAreaRenderer and PartyPanelRenderer get their own."""

    def __init__(self) -> None:
        self._flash_cache: dict[tuple[int, int], pygame.Surface] = {}

    def apply(
        self,
        screen: pygame.Surface,
        target: Combatant,
        x: int, y: int, w: int, h: int,
        fx: BattleFx | None,
        sprite: pygame.Surface | None = None,
    ) -> None:
        if fx is None:
            return
        alpha = fx.flash_alpha(target)
        if alpha <= 0:
            return
        r, g, b = fx.flash_color(target)
        scale = alpha / 255.0
        tint = (int(r * scale), int(g * scale), int(b * scale))
        if sprite is not None:
            # Sprite branch: copy + BLEND_RGB_ADD. Pre-baking would explode
            # cache size across enemies × flash colors so the per-frame copy
            # is the lesser evil.
            overlay = sprite.copy()
            overlay.fill(tint, special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(overlay, (x, y))
        else:
            overlay = self._flash_cache.get((w, h))
            if overlay is None:
                overlay = pygame.Surface((w, h), pygame.SRCALPHA)
                self._flash_cache[(w, h)] = overlay
            overlay.fill((r, g, b, alpha))
            screen.blit(overlay, (x, y))
