# engine/battle/battle_enemy_area_renderer.py
#
# Draws the upper third of the battle screen: the floor strip, every active
# enemy sprite + HP bar, and the targeting reticle when SELECT_TARGET is
# active. Owns the KO-ghost cache (a 80-alpha copy of each enemy's idle
# sprite) and shares a HitFlash helper with the party panel renderer.

from __future__ import annotations

import math
import time

import pygame

from engine.battle.battle_asset_cache import BattleAssetCache
from engine.battle.battle_fx import BattleFx
from engine.battle.battle_hit_flash import HitFlash
from engine.battle.battle_state import BattleState, BattlePhase
from engine.battle.combatant import Combatant
from engine.battle.constants import ENEMY_AREA_H, ENEMY_LAYOUTS
from engine.battle.battle_renderer_constants import (
    C_FLOOR, C_HP_LOW, C_HP_OK,
)
from engine.common.color_constants import HP_LOW_THRESHOLD

# Idle "breathing" squash: vertical compression on a sine wave with the
# feet anchored to the floor. Sprite height is shortened by 0..MAX px on
# a slow cycle; the draw position is shifted down by the same amount so
# the bottom edge doesn't move. Per-enemy phase offset prevents a row of
# enemies from squashing in lockstep.
SQUASH_MAX_PX     = 2
SQUASH_PERIOD_SEC = 1.4
SQUASH_PHASE_OFFSET = 0.6
# Fraction of the sprite (from the top) that participates in the squash —
# head, shoulders, and upper chest move; waist/legs/feet stay planted.
SQUASH_TOP_FRACTION = 0.60

# Attack-triggered animations. LPC layout:
#   row 2 = spellcast DOWN (7 frames, cols 0-6)
#   row 6 = thrust    DOWN (8 frames, cols 0-7)
SPELLCAST_ROW_OFFSET = 0   # Direction.DOWN.value (=2) + offset 0 → row 2
SPELLCAST_FRAME_COUNT = 7
THRUST_ROW_OFFSET    = 4   # Direction.DOWN.value (=2) + offset 4 → row 6
THRUST_FRAME_COUNT   = 8


class EnemyAreaRenderer:
    def __init__(
        self,
        assets: BattleAssetCache,
        screen_w: int,
        hit_flash: HitFlash,
    ) -> None:
        self._assets = assets
        self._screen_w = screen_w
        self._hit_flash = hit_flash
        # Pre-baked KO ghost per enemy, invalidated when the source sprite
        # identity changes.
        self._ko_cache: dict[str, tuple[pygame.Surface, pygame.Surface]] = {}

    def draw(
        self,
        screen: pygame.Surface,
        state: BattleState,
        target_pool: list[Combatant],
        target_sel: int,
        has_bg: bool,
        fx: BattleFx | None,
    ) -> None:
        if not has_bg:
            pygame.draw.rect(screen, C_FLOOR,
                             (0, ENEMY_AREA_H - 60, self._screen_w, 60))
            pygame.draw.line(screen, (42, 42, 68),
                             (0, ENEMY_AREA_H - 60), (self._screen_w, ENEMY_AREA_H - 60))

        enemies = state.enemies
        n = len(enemies)
        offsets = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])
        cx = self._screen_w // 2
        cy = ENEMY_AREA_H // 2 + 10

        for i, enemy in enumerate(enemies):
            ox, oy = offsets[i]
            self._draw_enemy(screen, enemy, cx + ox, cy + oy, i,
                             state, target_pool, target_sel, fx=fx)

    def _draw_enemy(
        self, screen: pygame.Surface, enemy: Combatant,
        cx: int, cy: int, index: int,
        state: BattleState,
        target_pool: list[Combatant], target_sel: int,
        fx: BattleFx | None,
    ) -> None:
        w, h = self._assets.enemy_rect_size(enemy)
        rx, ry = cx - w // 2, cy - h // 2

        shake_dx = fx.shake_offset(enemy) if fx else 0
        attack = fx.attack_progress(enemy) if fx and not enemy.is_ko else None
        squash = 0
        if not enemy.is_ko and attack is None:
            phase = time.monotonic() * (2 * math.pi / SQUASH_PERIOD_SEC) + index * SQUASH_PHASE_OFFSET
            squash = round(SQUASH_MAX_PX * (0.5 - 0.5 * math.cos(phase)))
        sx, sy = rx + shake_dx, ry + squash

        sprite = self._assets.load_enemy_sprite(enemy)
        if sprite is not None:
            anim_frame = self._attack_frame(enemy, attack) if attack else None
            if anim_frame is not None:
                screen.blit(anim_frame, (sx, ry))
                self._hit_flash.apply(screen, enemy, sx, ry,
                                      anim_frame.get_width(), anim_frame.get_height(),
                                      fx, sprite=anim_frame)
            else:
                img = self._ko_ghost(enemy.id, sprite) if enemy.is_ko else sprite
                if squash > 0:
                    # Squash only the top portion of the sprite so the
                    # legs/feet stay pixel-exact; pygame.transform.scale on
                    # the full image drops sample rows from the bottom
                    # too, which reads as feet drifting up.
                    iw, ih = img.get_width(), img.get_height()
                    top_h = int(ih * SQUASH_TOP_FRACTION)
                    top = img.subsurface((0, 0, iw, top_h))
                    bot = img.subsurface((0, top_h, iw, ih - top_h))
                    top_squashed = pygame.transform.scale(top, (iw, top_h - squash))
                    screen.blit(top_squashed, (sx, ry + squash))
                    screen.blit(bot, (sx, ry + top_h))
                    self._hit_flash.apply(screen, enemy, sx, ry + squash,
                                          iw, ih - squash, fx, sprite=img)
                else:
                    screen.blit(img, (sx, sy))
                    self._hit_flash.apply(screen, enemy, sx, sy,
                                          img.get_width(), img.get_height(), fx, sprite=img)
        else:
            base_col = (30, 30, 40) if enemy.is_ko else (42, 58, 90)
            bdr_col  = (50, 50, 60) if enemy.is_ko else (74, 106, 154)
            pygame.draw.rect(screen, base_col, (sx, sy, w, h), border_radius=4)
            pygame.draw.rect(screen, bdr_col,  (sx, sy, w, h), 1, border_radius=4)
            self._hit_flash.apply(screen, enemy, sx, sy, w, h, fx)

        bar_w = w
        bar_x = cx - bar_w // 2
        bar_y = ry + h + 4
        bar_h = 18
        pygame.draw.rect(screen, (40, 40, 40), (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6), 2, border_radius=6)
        pygame.draw.rect(screen, (200, 200, 200), (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2), 2, border_radius=4)
        pygame.draw.rect(screen, (42, 42, 42), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        hp_fill = int(bar_w * enemy.hp_pct)
        hp_col  = C_HP_OK if enemy.hp_pct > HP_LOW_THRESHOLD else C_HP_LOW
        if hp_fill > 0 and not enemy.is_ko:
            pygame.draw.rect(screen, hp_col, (bar_x, bar_y, hp_fill, bar_h), border_radius=3)

        name_surf = self._assets.font_enemy.render(enemy.name, True, (255, 255, 255))
        name_x = bar_x + bar_w // 2 - name_surf.get_width() // 2
        name_y = bar_y + bar_h // 2 - name_surf.get_height() // 2
        shadow = self._assets.font_enemy.render(enemy.name, True, (0, 0, 0))
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            screen.blit(shadow, (name_x + ox, name_y + oy))
        screen.blit(name_surf, (name_x, name_y))

        if (state.phase == BattlePhase.SELECT_TARGET
                and target_pool
                and index < len(target_pool)
                and target_pool[target_sel] is enemy):
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, ry - 2, w + 4, h + 4), 2, border_radius=5)

    def _attack_frame(
        self, enemy: Combatant, attack: tuple[str, float],
    ) -> pygame.Surface | None:
        kind, progress = attack
        if kind == "thrust":
            row_offset, count = THRUST_ROW_OFFSET, THRUST_FRAME_COUNT
        else:
            row_offset, count = SPELLCAST_ROW_OFFSET, SPELLCAST_FRAME_COUNT
        frames = self._assets.load_enemy_attack_frames(enemy, row_offset, count)
        if not frames:
            return None
        idx = min(len(frames) - 1, int(progress * len(frames)))
        return frames[idx]

    def _ko_ghost(self, enemy_id: str, sprite: pygame.Surface) -> pygame.Surface:
        """Return a 80-alpha copy of the sprite, baked once per (enemy, sprite)."""
        cached = self._ko_cache.get(enemy_id)
        if cached is not None and cached[0] is sprite:
            return cached[1]
        ghost = sprite.copy()
        ghost.set_alpha(80)
        self._ko_cache[enemy_id] = (sprite, ghost)
        return ghost
