# engine/battle/post_battle_scene.py
#
# Victory / spoils screen shown after a won battle. Drawing lives in
# post_battle_renderer.PostBattleRenderer; this scene owns the flow:
#   1. The EXP "tally" animates on entry; pressing confirm skips it.
#   2. If anyone levelled up, a centered modal then steps through each grown
#      member showing the new level and a before -> after stat comparison.
#   3. A final confirm continues to the world map.

from __future__ import annotations

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.battle.battle_rewards import BattleRewards
from engine.battle.post_battle_renderer import PostBattleRenderer


class PostBattleScene(Scene):
    """
    Displays EXP gained, level-ups, and loot after a victorious battle.
    Player presses SPACE / ENTER / Z to continue → world map.
    """

    def __init__(
        self,
        rewards: BattleRewards,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_continue: callable,
        sfx_manager,
    ) -> None:
        self._rewards = rewards
        self._scene_manager = scene_manager
        self._registry = registry
        self._on_continue = on_continue
        self._sfx_manager = sfx_manager
        self._renderer = PostBattleRenderer(rewards)

        # animate the EXP tally on entry
        self._exp_fill: float = 0.0      # 0.0 -> 1.0
        self._exp_done: bool = False
        self._ready_to_exit: bool = False

        # level-up modal sequence (shown once the tally completes)
        self._lu_queue = self._build_lu_queue()
        self._lu_index: int = 0
        self._lu_active: bool = False

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                              pygame.K_KP_ENTER, pygame.K_z):
                self._sfx_manager.play("confirm")
                if not self._exp_done:
                    # skip the tally animation
                    self._exp_fill = 1.0
                    self._exp_done = True
                    self._on_tally_done()
                elif self._lu_active:
                    # advance through the level-up modals
                    self._lu_index += 1
                    if self._lu_index >= len(self._lu_queue):
                        self._lu_active = False
                        self._ready_to_exit = True
                elif self._ready_to_exit:
                    self._on_continue()

    def _on_tally_done(self) -> None:
        """Called once the EXP tally is full. Opens the level-up modal
        sequence if anyone grew, otherwise readies the continue prompt."""
        if self._lu_queue:
            self._lu_active = True
            self._lu_index = 0
        else:
            self._ready_to_exit = True

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if not self._exp_done:
            self._exp_fill = min(1.0, self._exp_fill + delta * 0.6)
            if self._exp_fill >= 1.0:
                self._exp_done = True
                self._on_tally_done()

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        lu_entry = (
            self._lu_queue[self._lu_index]
            if self._lu_active and self._lu_index < len(self._lu_queue)
            else None
        )
        self._renderer.render(
            screen,
            shown_map=self._exp_shown(),
            lu_active=self._lu_active,
            lu_entry=lu_entry,
            lu_index=self._lu_index,
            lu_total=len(self._lu_queue),
            ready_to_exit=self._ready_to_exit,
        )

    # ── EXP tally ─────────────────────────────────────────────

    def _exp_shown(self) -> dict[str, int]:
        """How much EXP each member has visibly received so far.

        Members are paid out sequentially as `_exp_fill` advances 0 → 1, so the
        pool drains one member at a time. The header subtracts these from the
        total, decrementing to zero exactly when the last member is paid.
        """
        results = self._rewards.member_results
        total = sum(r.exp_gained for r in results)
        target = self._exp_fill * total      # EXP awarded across the party so far
        running = 0.0
        out: dict[str, int] = {}
        for r in results:
            take = min(float(r.exp_gained), max(0.0, target - running))
            out[r.member_id] = int(round(take))
            running += r.exp_gained
        return out

    # ── Level-up modal sequence ───────────────────────────────

    def _build_lu_queue(self) -> list[dict]:
        """One entry per member who gained at least one level, each holding the
        new level and before -> after totals for every stat. Built once at
        construction so the modal can step through it."""
        queue: list[dict] = []
        for r in self._rewards.member_results:
            if not r.level_ups:
                continue
            last = r.level_ups[-1]
            # "before" is the post-growth total minus everything gained here.
            stats = [
                ("HP", last.hp_max, sum(lu.hp_gained for lu in r.level_ups)),
                ("MP", last.mp_max, sum(lu.mp_gained for lu in r.level_ups)),
                ("STR", last.str_total, sum(lu.str_gained for lu in r.level_ups)),
                ("DEX", last.dex_total, sum(lu.dex_gained for lu in r.level_ups)),
                ("CON", last.con_total, sum(lu.con_gained for lu in r.level_ups)),
                ("INT", last.int_total, sum(lu.int_gained for lu in r.level_ups)),
            ]
            queue.append({
                "member_id": r.member_id,
                "member_name": r.member_name,
                "old_level": r.level_ups[0].old_level,
                "new_level": last.new_level,
                "stats": [(label, total - gained, total) for label, total, gained in stats],
            })
        return queue
