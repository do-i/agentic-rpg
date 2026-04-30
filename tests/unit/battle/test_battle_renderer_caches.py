# tests/unit/core/battle/test_battle_renderer_caches.py
#
# Targets the per-frame allocation caches added in step 4 of the code review:
# damage-float surface cache, KO-ghost cache, hit-flash overlay cache, and
# the fade / quit-dim overlays in WorldMapRenderer.

from __future__ import annotations

import pygame
import pytest
from unittest.mock import MagicMock, patch

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


class TestKoGhostCache:
    """KO ghost cache now lives on the EnemyAreaRenderer."""

    def test_returns_cached_ghost_for_same_sprite(self):
        renderer, _ = _make_renderer()
        sprite = pygame.Surface((32, 32), pygame.SRCALPHA)
        ghost1 = renderer._enemy_area._ko_ghost("goblin", sprite)
        ghost2 = renderer._enemy_area._ko_ghost("goblin", sprite)
        assert ghost1 is ghost2

    def test_rebuilds_on_sprite_change(self):
        renderer, _ = _make_renderer()
        s1 = pygame.Surface((32, 32), pygame.SRCALPHA)
        s2 = pygame.Surface((32, 32), pygame.SRCALPHA)
        g1 = renderer._enemy_area._ko_ghost("goblin", s1)
        g2 = renderer._enemy_area._ko_ghost("goblin", s2)
        assert g1 is not g2

    def test_separate_enemies_have_separate_entries(self):
        renderer, _ = _make_renderer()
        sprite = pygame.Surface((32, 32), pygame.SRCALPHA)
        renderer._enemy_area._ko_ghost("goblin", sprite)
        renderer._enemy_area._ko_ghost("orc", sprite)
        assert set(renderer._enemy_area._ko_cache.keys()) == {"goblin", "orc"}


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
    def _render_world(self, renderer, screen, fade_alpha=0, quit_confirm=False):
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
            quit_confirm=quit_confirm,
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

    def test_quit_dim_surface_allocated_once(self):
        from engine.common import font_provider
        font_provider.init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})

        renderer = WorldMapRenderer()
        screen = pygame.Surface((320, 240), pygame.SRCALPHA)
        renderer._render_quit_confirm(screen)
        first = renderer._quit_dim_surf
        assert first is not None
        renderer._render_quit_confirm(screen)
        assert renderer._quit_dim_surf is first
