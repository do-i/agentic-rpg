# engine/battle/battle_damage_float_renderer.py
#
# Renders the floating damage/heal numbers that drift up and fade out over
# every hit. Caches the source (shadow, foreground) pair per DamageFloat
# instance; fade alpha is applied to per-frame copies so the cached glyphs
# never carry framebuffer-dependent surface alpha state.

from __future__ import annotations

import pygame

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_state import BattleState


class DamageFloatRenderer:
    def __init__(self, assets: BattleAssetCache) -> None:
        self._assets = assets

    def draw(self, screen: pygame.Surface, state: BattleState) -> None:
        for f in state.damage_floats:
            if f.alpha <= 0:
                continue
            pair = f.cached_surfaces
            if pair is None:
                shadow = self._render_glyph(f.text, (0, 0, 0))
                surf = self._render_glyph(f.text, f.color)
                pair = (shadow, surf)
                f.cached_surfaces = pair
            shadow, surf = pair
            shadow_frame = self._with_alpha(shadow, f.alpha)
            for ox, oy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2)):
                screen.blit(shadow_frame, (f.x + ox, f.y + oy))
            screen.blit(self._with_alpha(surf, f.alpha), (f.x, f.y))

    def _render_glyph(self, text: str, color: tuple[int, int, int]) -> pygame.Surface:
        return self._assets.font_dmg.render(text, True, color).convert_alpha()

    @staticmethod
    def _with_alpha(source: pygame.Surface, alpha: int) -> pygame.Surface:
        if alpha >= 255:
            return source
        faded = source.copy()
        faded.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        return faded
