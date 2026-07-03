# engine/battle/battle_asset_cache.py
#
# Asset loading and caching for battle rendering: fonts, portraits,
# enemy sprites, and background images.

from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pygame
from engine.common.font_provider import get_fonts

from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_SIZES
from engine.battle.battle_renderer_constants import PORTRAIT_SIZE
from engine.battle.ground_rect_catalog import GroundRect, GroundRectCatalog
from engine.party.party_data import load_party_entries
from engine.world.sprite_sheet import SpriteSheet, Direction

_log = logging.getLogger(__name__)


class BattleAssetCache:
    """Lazily loads and caches all assets needed by BattleRenderer."""

    def __init__(self, scenario_path: Path) -> None:
        self._scenario_path = scenario_path
        self._fonts_ready = False
        self._portraits: dict[str, pygame.Surface] = {}
        self._portrait_paths: dict[str, Path] | None = None
        self._enemy_size: dict[str, tuple] = {}
        self._enemy_sprites: dict[str, pygame.Surface | None] = {}
        self._enemy_sheets: dict[str, SpriteSheet | None] = {}
        self._enemy_anim_frames: dict[tuple[str, int, int], list[pygame.Surface]] = {}
        self._bg_cache: dict[str, pygame.Surface | None] = {}
        self._ground_rects: GroundRectCatalog | None = None

    # ── Fonts ─────────────────────────────────────────────────

    def init_fonts(self) -> None:
        if self._fonts_ready:
            return
        f = get_fonts()
        self.font_name  = f.get(14, bold=True)
        self.font_stat  = f.get(12)
        self.font_cmd   = f.get(16)
        self.font_sub   = f.get(14)
        self.font_turn  = f.get(13)
        self.font_msg   = f.get(18)
        self.font_dmg   = f.get(26, bold=True)
        self.font_enemy = f.get(13, bold=True)
        self.font_badge = f.get(9,  bold=True)
        self._fonts_ready = True

    # ── Portraits ─────────────────────────────────────────────

    def load_portrait(self, member_id: str) -> pygame.Surface | None:
        if member_id in self._portraits:
            return self._portraits[member_id]
        if self._portrait_paths is None:
            self._portrait_paths = {
                e["id"]: self._scenario_path / e["portrait"]
                for e in load_party_entries(self._scenario_path)
            }
        path = self._portrait_paths.get(member_id)
        if path is None or not path.exists():
            return None
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            img = pygame.transform.scale(img, (PORTRAIT_SIZE, PORTRAIT_SIZE))
            self._portraits[member_id] = img
            return img
        except (pygame.error, OSError) as e:
            _log.warning("Portrait load failed: %s — %s", path, e)
            return None

    # ── Enemy sprites ─────────────────────────────────────────

    def enemy_rect_size(self, enemy: Combatant) -> tuple:
        if enemy.id in self._enemy_size:
            return self._enemy_size[enemy.id]
        base = ENEMY_SIZES["large"] if enemy.boss else ENEMY_SIZES[enemy.size]
        scale = enemy.sprite_scale / 100.0
        size = (int(base[0] * scale), int(base[1] * scale))
        self._enemy_size[enemy.id] = size
        return size

    def load_enemy_sprite(self, enemy: Combatant) -> pygame.Surface | None:
        sprite_id = enemy.sprite_id or enemy.id
        if sprite_id in self._enemy_sprites:
            return self._enemy_sprites[sprite_id]
        sheet = self._load_enemy_sheet(sprite_id)
        if sheet is None:
            self._enemy_sprites[sprite_id] = None
            return None
        try:
            frame = sheet.get_frame(Direction.DOWN, 0)
            w, h = self.enemy_rect_size(enemy)
            scaled = self._scale_frame(frame, (w, h))
            self._enemy_sprites[sprite_id] = scaled
            return scaled
        except (pygame.error, KeyError, ValueError) as e:
            _log.warning("Enemy idle frame failed: %s — %s", sprite_id, e)
            self._enemy_sprites[sprite_id] = None
            return None

    def load_enemy_attack_frames(
        self, enemy: Combatant, row_offset: int, frame_count: int,
    ) -> list[pygame.Surface]:
        """Return the row's frames (cols 0..frame_count-1) scaled to the
        enemy's rect size. Cached per (sprite_id, row_offset, frame_count).
        Returns an empty list if the sheet can't be loaded."""
        sprite_id = enemy.sprite_id or enemy.id
        key = (sprite_id, row_offset, frame_count)
        if key in self._enemy_anim_frames:
            return self._enemy_anim_frames[key]
        sheet = self._load_enemy_sheet(sprite_id)
        if sheet is None:
            self._enemy_anim_frames[key] = []
            return []
        w, h = self.enemy_rect_size(enemy)
        frames: list[pygame.Surface] = []
        try:
            for col in range(frame_count):
                frame = sheet.get_frame(Direction.DOWN, col, row_offset=row_offset)
                frames.append(self._scale_frame(frame, (w, h)))
        except (pygame.error, KeyError, ValueError) as e:
            _log.warning("Enemy attack frames failed: %s row=%d — %s",
                         sprite_id, row_offset, e)
            frames = []
        self._enemy_anim_frames[key] = frames
        return frames

    @staticmethod
    def _scale_frame(frame: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        """Downscaling (pre-rendered battle sheets) filters smoothly;
        upscaling (legacy 64 px map sheets) stays nearest-neighbor to
        preserve the pixel-art look."""
        if frame.get_width() > size[0] and frame.get_height() > size[1]:
            return pygame.transform.smoothscale(frame, size)
        return pygame.transform.scale(frame, size)

    def _load_enemy_sheet(self, sprite_id: str) -> SpriteSheet | None:
        """Prefer a pre-rendered `<sprite_id>_battle.tsx` sheet (graded to
        match the battle backgrounds); fall back to the world-map sheet."""
        if sprite_id in self._enemy_sheets:
            return self._enemy_sheets[sprite_id]
        sprites_dir = self._scenario_path / "assets" / "sprites" / "enemies"
        tsx_path = sprites_dir / f"{sprite_id}_battle.tsx"
        if not tsx_path.exists():
            tsx_path = sprites_dir / f"{sprite_id}.tsx"
        if not tsx_path.exists():
            self._enemy_sheets[sprite_id] = None
            return None
        try:
            sheet: SpriteSheet | None = SpriteSheet(tsx_path)
        except (pygame.error, OSError, ParseError, KeyError, ValueError) as e:
            _log.warning("Enemy sprite sheet load failed: %s — %s", tsx_path, e)
            sheet = None
        self._enemy_sheets[sprite_id] = sheet
        return sheet

    # ── Backgrounds ───────────────────────────────────────────

    def load_background(self, bg_id: str) -> pygame.Surface | None:
        if bg_id in self._bg_cache:
            return self._bg_cache[bg_id]
        path = self._scenario_path / "assets" / "images" / "battle_bg" / f"{bg_id}.webp"
        if path.exists():
            try:
                self._bg_cache[bg_id] = pygame.image.load(str(path)).convert()
                return self._bg_cache[bg_id]
            except (pygame.error, OSError) as e:
                _log.warning("Battle background load failed: %s — %s", path, e)
        self._bg_cache[bg_id] = None
        return None

    # ── Ground rects ──────────────────────────────────────────

    def ground_rect(self, bg_id: str) -> GroundRect:
        if self._ground_rects is None:
            path = self._scenario_path / "data" / "battle_backgrounds.yaml"
            self._ground_rects = GroundRectCatalog(path)
        return self._ground_rects.get(bg_id)
