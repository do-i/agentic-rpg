# tests/unit/battle/test_battle_renderer_caches.py
#
# Targets the per-frame allocation caches added in step 4 of the code review:
# damage-float surface cache, hit-flash overlay cache, and the fade /
# quit-dim overlays in WorldMapRenderer.

from __future__ import annotations

import pygame
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from engine.battle.battle_damage_float_renderer import DamageFloatRenderer
from engine.battle.battle_state import BattleState, DamageFloat
from engine.world.world_map_renderer import WorldMapRenderer


@pytest.fixture(autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


# ──────────────────────────────────────────────────────────────
# BattleRenderer caches
# ──────────────────────────────────────────────────────────────


def _make_renderer():
    """Construct a BattleRenderer with a stubbed asset cache."""
    from engine.battle.battle_renderer import BattleRenderer
    with patch("engine.battle.battle_renderer.BattleAssetCache") as mock_cache:
        instance = MagicMock()
        # font_dmg.render returns a fresh small surface each call.
        instance.font_dmg.render.side_effect = lambda *a, **k: pygame.Surface((10, 10), pygame.SRCALPHA)
        mock_cache.return_value = instance
        renderer = BattleRenderer(scenario_path="ignored")
    return renderer, instance


class TestDamageFloatCache:
    """The (shadow, foreground) surface pair is cached on each DamageFloat
    instance — so the cache dies with the float and can't collide with a
    reused id()."""

    def test_renders_once_per_float(self):
        renderer, assets = _make_renderer()
        state = BattleState(party=[], enemies=[])
        f = DamageFloat("12", 0, 0, (255, 255, 255))
        state.damage_floats.append(f)

        screen = pygame.Surface((40, 40), pygame.SRCALPHA)
        renderer._damage_floats.draw(screen, state)
        renderer._damage_floats.draw(screen, state)
        renderer._damage_floats.draw(screen, state)

        # 1 shadow + 1 colored = 2 calls per cache miss; only one miss expected.
        assert assets.font_dmg.render.call_count == 2

    def test_surfaces_attached_to_float(self):
        renderer, _ = _make_renderer()
        state = BattleState(party=[], enemies=[])
        f = DamageFloat("12", 0, 0, (255, 255, 255))
        state.damage_floats.append(f)
        screen = pygame.Surface((40, 40), pygame.SRCALPHA)

        assert f.cached_surfaces is None
        renderer._damage_floats.draw(screen, state)
        assert f.cached_surfaces is not None

    def test_distinct_floats_get_distinct_entries(self):
        renderer, _ = _make_renderer()
        state = BattleState(party=[], enemies=[])
        a = DamageFloat("1", 0, 0, (255, 0, 0))
        b = DamageFloat("2", 0, 0, (0, 255, 0))
        state.damage_floats.extend([a, b])
        screen = pygame.Surface((40, 40), pygame.SRCALPHA)

        renderer._damage_floats.draw(screen, state)
        assert a.cached_surfaces is not None
        assert b.cached_surfaces is not None
        assert a.cached_surfaces is not b.cached_surfaces

    def test_cached_glyphs_do_not_keep_fade_alpha(self):
        renderer, _ = _make_renderer()
        state = BattleState(party=[], enemies=[])
        f = DamageFloat("12", 0, 0, (255, 255, 255), alpha=96)
        state.damage_floats.append(f)

        screen = pygame.Surface((40, 40))
        renderer._damage_floats.draw(screen, state)

        assert f.cached_surfaces is not None
        shadow, surf = f.cached_surfaces
        assert shadow.get_alpha() == 255
        assert surf.get_alpha() == 255

    def test_half_alpha_glyph_blends_into_opaque_framebuffer(self):
        class PixelFont:
            def render(self, _text, _antialias, color):
                surf = pygame.Surface((3, 3), pygame.SRCALPHA)
                surf.fill((0, 0, 0, 0))
                surf.set_at((1, 1), (*color, 255))
                return surf

        renderer = DamageFloatRenderer(SimpleNamespace(font_dmg=PixelFont()))
        state = BattleState(party=[], enemies=[])
        state.damage_floats.append(DamageFloat("7", 5, 5, (200, 40, 20), alpha=128))
        screen = pygame.Surface((20, 20))
        bg = (10, 20, 30)
        screen.fill(bg)

        renderer.draw(screen, state)

        assert screen.get_at((5, 6))[:3] == bg
        blended = screen.get_at((6, 6))[:3]
        assert bg[0] < blended[0] < 200
        assert bg[1] < blended[1] < 40
        assert 20 < blended[2] < bg[2]


class TestFlashCache:
    """Hit-flash cache now lives on the shared HitFlash helper."""

    def test_reuses_overlay_for_same_size(self):
        renderer, _ = _make_renderer()
        # Drive HitFlash.apply via a fake fx that flashes on a non-sprite enemy.
        fx = MagicMock()
        fx.flash_alpha.return_value = 200
        fx.flash_color.return_value = (255, 255, 255)
        screen = pygame.Surface((100, 100), pygame.SRCALPHA)

        target = MagicMock()
        renderer._hit_flash.apply(screen, target, 0, 0, 32, 32, fx, sprite=None)
        first = renderer._hit_flash._flash_cache[(32, 32)]
        renderer._hit_flash.apply(screen, target, 0, 0, 32, 32, fx, sprite=None)
        assert renderer._hit_flash._flash_cache[(32, 32)] is first

    def test_separate_size_makes_separate_overlay(self):
        renderer, _ = _make_renderer()
        fx = MagicMock()
        fx.flash_alpha.return_value = 200
        fx.flash_color.return_value = (255, 255, 255)
        screen = pygame.Surface((100, 100), pygame.SRCALPHA)
        target = MagicMock()
        renderer._hit_flash.apply(screen, target, 0, 0, 32, 32, fx, sprite=None)
        renderer._hit_flash.apply(screen, target, 0, 0, 64, 64, fx, sprite=None)
        assert set(renderer._hit_flash._flash_cache.keys()) == {(32, 32), (64, 64)}


# ──────────────────────────────────────────────────────────────
# WorldMapRenderer overlays
# ──────────────────────────────────────────────────────────────


class TestWorldMapOverlayReuse:
    def _render_world(self, renderer, screen, fade_alpha=0):
        # Minimal stubs satisfying the renderer's contract.
        tile_map = MagicMock()
        tile_map.render = MagicMock()
        tile_map.portals = []
        camera = MagicMock(offset_x=0, offset_y=0)
        player = MagicMock()
        player.pixel_position = MagicMock(x=0, y=0)
        player.render = MagicMock()
        renderer.render(
            screen=screen,
            tile_map=tile_map,
            camera=camera,
            player=player,
            npcs=[],
            enemy_sprites=[],
            overlays=[],
            dialogue=None,
            fade_alpha=fade_alpha,
        )

    def test_fade_surface_allocated_once(self):
        renderer = WorldMapRenderer()
        screen = pygame.Surface((320, 240), pygame.SRCALPHA)
        self._render_world(renderer, screen, fade_alpha=128)
        first = renderer._fade_surf
        assert first is not None
        self._render_world(renderer, screen, fade_alpha=64)
        assert renderer._fade_surf is first

    def test_fade_surface_not_built_when_alpha_zero(self):
        renderer = WorldMapRenderer()
        screen = pygame.Surface((320, 240), pygame.SRCALPHA)
        self._render_world(renderer, screen, fade_alpha=0)
        assert renderer._fade_surf is None
