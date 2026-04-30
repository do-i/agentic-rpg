# tests/unit/core/battle/test_post_battle_scene.py

from __future__ import annotations

import pytest
import pygame
from unittest.mock import MagicMock

from engine.battle.post_battle_scene import PostBattleScene
from engine.battle.battle_rewards_data import (
    BattleRewards, MemberExpResult, LootResult, LevelUpResult,
)
from engine.common.font_provider import init_fonts


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    init_fonts(None, {"small": 12, "medium": 16, "large": 20, "xlarge": 28})
    yield
    pygame.quit()


def make_rewards(
    total_exp: int = 100,
    members: list[MemberExpResult] | None = None,
    mc_drops: list[dict] | None = None,
    item_drops: list[dict] | None = None,
) -> BattleRewards:
    return BattleRewards(
        total_exp=total_exp,
        member_results=members or [],
        loot=LootResult(mc_drops=mc_drops or [], item_drops=item_drops or []),
    )


def make_scene(rewards=None, sfx=None) -> tuple[PostBattleScene, MagicMock]:
    on_continue = MagicMock()
    scene = PostBattleScene(
        rewards=rewards or make_rewards(),
        scene_manager=MagicMock(),
        registry=MagicMock(),
        on_continue=on_continue,
        sfx_manager=sfx,
    )
    return scene, on_continue


def keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


# ── EXP fill animation ────────────────────────────────────────

class TestExpFillAnimation:
    def test_fill_advances_with_delta(self):
        scene, _ = make_scene()
        scene.update(0.5)
        assert 0 < scene._exp_fill < 1.0

    def test_fill_completes_marks_done_and_ready(self):
        scene, _ = make_scene()
        scene.update(2.0)  # 2 sec * 0.6 rate clamps to 1.0
        assert scene._exp_done is True
        assert scene._ready_to_exit is True

    def test_after_done_update_does_nothing(self):
        scene, _ = make_scene()
        scene.update(2.0)
        prev = scene._exp_fill
        scene.update(0.5)
        assert scene._exp_fill == prev


# ── Skip-to-end on first key press ────────────────────────────

class TestSkipAnimation:
    def test_first_press_skips_fill(self):
        scene, on_continue = make_scene()
        scene.handle_events([keydown(pygame.K_RETURN)])
        assert scene._exp_done is True
        assert scene._exp_fill == 1.0
        assert scene._ready_to_exit is True
        # Single press only skips; doesn't continue immediately.
        on_continue.assert_not_called()

    def test_second_press_invokes_continue(self):
        scene, on_continue = make_scene()
        scene.handle_events([keydown(pygame.K_RETURN)])
        scene.handle_events([keydown(pygame.K_RETURN)])
        on_continue.assert_called_once()

    def test_z_key_also_works(self):
        scene, on_continue = make_scene()
        scene.handle_events([keydown(pygame.K_z)])
        scene.handle_events([keydown(pygame.K_z)])
        on_continue.assert_called_once()

    def test_space_key_also_works(self):
        scene, on_continue = make_scene()
        scene.handle_events([keydown(pygame.K_SPACE)])
        scene.handle_events([keydown(pygame.K_SPACE)])
        on_continue.assert_called_once()

    def test_other_keys_ignored(self):
        scene, on_continue = make_scene()
        scene.handle_events([keydown(pygame.K_a)])
        assert scene._exp_done is False
        on_continue.assert_not_called()

    def test_confirm_sfx_played_on_keypress(self):
        sfx = MagicMock()
        scene, _ = make_scene(sfx=sfx)
        scene.handle_events([keydown(pygame.K_RETURN)])
        sfx.play.assert_called_with("confirm")


# ── Render smoke ──────────────────────────────────────────────

class TestRender:
    def test_render_with_empty_loot_does_not_crash(self):
        scene, _ = make_scene()
        screen = pygame.Surface((640, 480))
        scene.render(screen)

    def test_render_with_level_up_does_not_crash(self):
        lvup = LevelUpResult(
            member_id="hero", member_name="Hero",
            old_level=1, new_level=2,
            hp_gained=5, mp_gained=2,
            str_gained=1, dex_gained=1, con_gained=1, int_gained=1,
        )
        member = MemberExpResult(
            member_id="hero", member_name="Hero",
            exp_gained=100, level_ups=[lvup],
        )
        rewards = make_rewards(members=[member])
        scene, _ = make_scene(rewards=rewards)
        screen = pygame.Surface((640, 480))
        scene.render(screen)

    def test_render_with_loot_drops_does_not_crash(self):
        rewards = make_rewards(
            mc_drops=[{"size": "S", "qty": 2}],
            item_drops=[{"id": "rat_tail", "name": "Rat Tail", "qty": 1}],
        )
        scene, _ = make_scene(rewards=rewards)
        screen = pygame.Surface((640, 480))
        scene.render(screen)

    def test_render_with_ko_member_does_not_crash(self):
        member = MemberExpResult(
            member_id="hero", member_name="Hero",
            exp_gained=0,  # 0 EXP → KO marker
            level_ups=[],
        )
        rewards = make_rewards(members=[member])
        scene, _ = make_scene(rewards=rewards)
        screen = pygame.Surface((640, 480))
        scene.render(screen)
