# engine/battle/battle_asset_cache.py
#
# Asset loading and caching for battle rendering: fonts, portraits,
# enemy sprites, and background images.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_SIZES
from engine.battle.battle_renderer_constants import PORTRAIT_SIZE
from engine.world.sprite_sheet import SpriteSheet, Direction


class BattleAssetCache:
    """Lazily loads and caches all assets needed by BattleRenderer."""

    def __init__(self, scenario_path: Path) -> None:
        self._scenario_path = scenario_path
        self._fonts_ready = False
        self._portraits: dict[str, pygame.Surface] = {}
        self._enemy_size: dict[str, tuple] = {}
        self._enemy_sprites: dict[str, pygame.Surface | None] = {}
        self._bg_cache: dict[str, pygame.Surface | None] = {}

    # ── Fonts ─────────────────────────────────────────────────

    def init_fonts(self) -> None:
        if self._fonts_ready:
            return
        self.font_name  = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_stat  = pygame.font.SysFont("Arial", 12)
        self.font_cmd   = pygame.font.SysFont("Arial", 16)
        self.font_sub   = pygame.font.SysFont("Arial", 14)
        self.font_turn  = pygame.font.SysFont("Arial", 13)
        self.font_msg   = pygame.font.SysFont("Arial", 18)
        self.font_dmg   = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_enemy = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_badge = pygame.font.SysFont("Arial", 9,  bold=True)
        self._fonts_ready = True

    # ── Portraits ─────────────────────────────────────────────

    def load_portrait(self, member_id: str) -> pygame.Surface | None:
        if member_id in self._portraits:
            return self._portraits[member_id]
        path = self._scenario_path / "assets" / "images" / f"{member_id}_profile.png"
        if not path.exists():
            return None
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            img = pygame.transform.scale(img, (PORTRAIT_SIZE, PORTRAIT_SIZE))
            self._portraits[member_id] = img
            return img
        except Exception:
            return None

    # ── Enemy sprites ─────────────────────────────────────────

    def enemy_rect_size(self, enemy: Combatant) -> tuple:
        if enemy.id in self._enemy_size:
            return self._enemy_size[enemy.id]
        if enemy.boss:
            base = ENEMY_SIZES["large"]
        else:
            idx = len(enemy.name) % 3
            base = [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]
        scale = enemy.sprite_scale / 100.0
        return (int(base[0] * scale), int(base[1] * scale))

    def load_enemy_sprite(self, enemy: Combatant) -> pygame.Surface | None:
        sprite_id = enemy.sprite_id or enemy.id
        if sprite_id in self._enemy_sprites:
            return self._enemy_sprites[sprite_id]
        tsx_path = self._scenario_path / "assets" / "sprites" / "enemies" / f"{sprite_id}.tsx"
        if not tsx_path.exists():
            self._enemy_sprites[sprite_id] = None
            return None
        try:
            sheet = SpriteSheet(tsx_path)
            frame = sheet.get_frame(Direction.DOWN, 0)
            w, h = self.enemy_rect_size(enemy)
            scaled = pygame.transform.scale(frame, (w, h))
            self._enemy_sprites[sprite_id] = scaled
            return scaled
        except Exception:
            self._enemy_sprites[sprite_id] = None
            return None

    # ── Backgrounds ───────────────────────────────────────────

    def load_background(self, bg_id: str) -> pygame.Surface | None:
        if bg_id in self._bg_cache:
            return self._bg_cache[bg_id]
        path = self._scenario_path / "assets" / "images" / "battle_bg" / f"{bg_id}.webp"
        if path.exists():
            try:
                self._bg_cache[bg_id] = pygame.image.load(str(path)).convert()
                return self._bg_cache[bg_id]
            except Exception:
                pass
        self._bg_cache[bg_id] = None
        return None
