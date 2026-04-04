# engine/core/scenes/battle_scene.py
#
# Phase 4 — Battle system
# Changes from previous version:
#   - RewardCalculator wired in after victory
#   - Party state synced back to GameState after battle
#   - Launches PostBattleScene on win, world_map on defeat
#   - Boss flag set on victory if present

from __future__ import annotations

import random

import pygame
from pathlib import Path

from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.battle.combatant import Combatant, StatusEffect
from engine.core.battle.battle_state import BattleState, BattlePhase
from engine.core.battle.battle_rewards import RewardCalculator
from engine.core.state.game_state_holder import GameStateHolder
from engine.core.encounter.encounter_manager import EncounterManager
from engine.core.scenes.post_battle_scene import PostBattleScene

# ── Layout ────────────────────────────────────────────────────
ENEMY_AREA_H    = int(Settings.SCREEN_HEIGHT * 0.65)
BOTTOM_H        = Settings.SCREEN_HEIGHT - ENEMY_AREA_H
PARTY_W         = Settings.SCREEN_WIDTH // 2
CMD_W           = Settings.SCREEN_WIDTH - PARTY_W

PORTRAIT_SIZE   = 36
ROW_H           = 44
ROW_PAD         = 8
BAR_H           = 6

STATUS_COLORS = {
    StatusEffect.POISON:  ((51, 102, 51),  (170, 255, 170), "PSN"),
    StatusEffect.SLEEP:   ((68, 68, 170),  (204, 204, 255), "zzz"),
    StatusEffect.STUN:    ((120, 90, 20),  (255, 220, 100), "STN"),
    StatusEffect.SILENCE: ((100, 60, 100), (220, 180, 220), "SIL"),
}

# ── Colors ────────────────────────────────────────────────────
C_BG           = (13,  13,  26)
C_FLOOR        = (17,  17,  40)
C_PANEL_LINE   = (51,  51,  51)
C_ROW_ACTIVE   = (42,  26,  26)
C_ROW_NORMAL   = (26,  26,  42)
C_BORDER_ACT   = (204, 68,  68)
C_BORDER_NORM  = (51,  51,  68)
C_CMD_SEL_BG   = (42,  32,  64)
C_CMD_SEL_BDR  = (119, 85,  204)
C_TEXT         = (238, 238, 238)
C_TEXT_MUT     = (170, 170, 170)
C_TEXT_DIM     = (102, 102, 102)
C_HP_OK        = (68,  170, 68)
C_HP_LOW       = (204, 68,  68)
C_MP           = (68,  102, 204)
C_HP_LABEL_OK  = (136, 204, 136)
C_HP_LABEL_LOW = (204, 136, 136)
C_MP_LABEL     = (136, 136, 204)
C_DMG_PHYS     = (255, 180, 80)
C_DMG_MAGIC    = (140, 180, 255)
C_HEAL         = (100, 220, 100)

HP_LOW_THRESHOLD = 0.35

ENEMY_LAYOUTS = {
    1: [(0,   0)],
    2: [(-80, 0),  (80,  0)],
    3: [(-110, -30), (0, 20), (110, -20)],
    4: [(-140, -20), (-45, 20), (45, -20), (140, 20)],
    5: [(-160, -30), (-80, 20), (0, -10), (80, 20), (160, -30)],
}

ENEMY_SIZES = {
    "boss":   (96, 96),
    "large":  (80, 80),
    "medium": (64, 64),
    "small":  (52, 52),
}


class BattleScene(Scene):
    """
    Phase 4 — battle screen.
    On victory: calculates rewards, syncs party state, launches PostBattleScene.
    On defeat: returns to world map (Game Over stub — Phase 4).
    """

    def __init__(
        self,
        battle_state: BattleState,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        holder: GameStateHolder,
        scenario_path: str = "",
        boss_flag: str = "",
    ) -> None:
        self._state = battle_state
        self._scene_manager = scene_manager
        self._registry = registry
        self._holder = holder
        self._scenario_path = Path(scenario_path)
        self._boss_flag = boss_flag
        self._reward_calc = RewardCalculator()

        self._fonts_ready = False
        self._portraits: dict[str, pygame.Surface] = {}
        self._enemy_size: dict[str, tuple] = {}

        self._cmd_items: list[str] = ["Attack", "Spell", "Item", "Run"]
        self._cmd_sel: int = 0
        self._sub_items: list[dict] = []
        self._sub_sel: int = 0
        self._target_pool: list[Combatant] = []
        self._target_sel: int = 0
        self._resolve_timer: float = 0.0
        self._resolve_msg: str = ""

        self._state.build_turn_order()
        # for p in self._state.party:
        #     print(f"[DEBUG] Party member {p.name}: HP={p.hp}/{p.hp_max}")
        #     p.hp = 100
        #     p.hp_max = 200
        active = self._state.active
        print(f"[BATTLE START] First active: {active.name if active else 'None'} | is_enemy={active.is_enemy if active else False}")
        if active and active.is_enemy:
            self._state.phase = BattlePhase.ENEMY_TURN
            self._resolve_enemy_turn()   # enemy acts immediately on first turn
        else:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._cmd_sel = 0



    # ── Font / asset init ─────────────────────────────────────

    def _init_fonts(self) -> None:
        self._font_name  = pygame.font.SysFont("Arial", 14, bold=True)
        self._font_stat  = pygame.font.SysFont("Arial", 12)
        self._font_cmd   = pygame.font.SysFont("Arial", 16)
        self._font_sub   = pygame.font.SysFont("Arial", 14)
        self._font_turn  = pygame.font.SysFont("Arial", 13)
        self._font_msg   = pygame.font.SysFont("Arial", 13)
        self._font_dmg   = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_enemy = pygame.font.SysFont("Arial", 11)
        self._font_badge = pygame.font.SysFont("Arial", 9,  bold=True)
        self._fonts_ready = True

    def _load_portrait(self, member_id: str) -> pygame.Surface | None:
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

    def _enemy_rect_size(self, enemy: Combatant) -> tuple:
        if enemy.id in self._enemy_size:
            return self._enemy_size[enemy.id]
        if enemy.boss:
            return ENEMY_SIZES["large"]
        idx = len(enemy.name) % 3
        return [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]
    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if not events:
            return

        for event in events:
            if event.type == pygame.QUIT:
                # Let the main loop handle this if needed
                continue

            if event.type != pygame.KEYDOWN:
                continue

            phase = self._state.phase

            # Global escape handling
            if event.key == pygame.K_ESCAPE:
                if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM, BattlePhase.SELECT_TARGET):
                    self._state.phase = BattlePhase.PLAYER_TURN
                    self._sub_items.clear()
                    continue
                elif phase == BattlePhase.PLAYER_TURN:
                    self._attempt_run()
                    continue

            # Phase-specific handling
            if phase == BattlePhase.PLAYER_TURN:
                self._handle_cmd(event.key)
            elif phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
                self._handle_sub(event.key)
            elif phase == BattlePhase.SELECT_TARGET:
                self._handle_target(event.key)
            elif phase == BattlePhase.RESOLVE:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self._resolve_timer = 0.0
            elif phase in (BattlePhase.POST_BATTLE, BattlePhase.GAME_OVER):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    if phase == BattlePhase.GAME_OVER:
                        self._return_to_world_map()
                    # PostBattleScene handles its own continue logic

    def _handle_cmd(self, key: int) -> None:
        active = self._state.active
        if active is None or active.is_enemy:
            return
        if key == pygame.K_UP:
            self._cmd_sel = max(0, self._cmd_sel - 1)
        elif key == pygame.K_DOWN:
            self._cmd_sel = min(len(self._cmd_items) - 1, self._cmd_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RIGHT):
            self._confirm_cmd()

    def _confirm_cmd(self) -> None:
        label  = self._cmd_items[self._cmd_sel]
        active = self._state.active
        if label == "Attack":
            self._target_pool = self._state.alive_enemies()
            self._target_sel  = 0
            self._state.pending_action = {"type": "attack", "source": active}
            self._state.phase = BattlePhase.SELECT_TARGET
        elif label == "Spell":
            if active and active.mp_max > 0:
                self._open_spell_menu(active)
        elif label == "Item":
            self._open_item_menu()
        elif label == "Run":
            self._attempt_run()

    def _open_spell_menu(self, active: Combatant) -> None:
        self._sub_items = []
        for ab in active.abilities:
            if ab.get("type") not in ("spell", "heal", "buff", "debuff", "utility"):
                continue
            cost = ab.get("mp_cost", 0)
            self._sub_items.append({
                "label":    ab["name"],
                "mp_cost":  cost,
                "data":     ab,
                "disabled": active.mp < cost,
            })
        self._sub_sel = 0
        self._state.phase = BattlePhase.SELECT_SPELL

    def _open_item_menu(self) -> None:
        # stub — Phase 6 wires real repository items
        self._sub_items = [
            {"label": "Potion",    "qty": 5, "data": {"id": "potion"},    "disabled": False},
            {"label": "Hi-Potion", "qty": 3, "data": {"id": "hi_potion"}, "disabled": False},
            {"label": "Antidote",  "qty": 2, "data": {"id": "antidote"},  "disabled": False},
        ]
        self._sub_sel = 0
        self._state.phase = BattlePhase.SELECT_ITEM

    def _handle_sub(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_LEFT):
            self._state.phase = BattlePhase.PLAYER_TURN
            return
        if key == pygame.K_UP:
            self._sub_sel = max(0, self._sub_sel - 1)
        elif key == pygame.K_DOWN:
            self._sub_sel = min(len(self._sub_items) - 1, self._sub_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_RIGHT):
            self._confirm_sub()

    def _confirm_sub(self) -> None:
        if not self._sub_items:
            return
        item    = self._sub_items[self._sub_sel]
        if item.get("disabled"):
            return
        active  = self._state.active
        phase   = self._state.phase
        ab_data = item.get("data", {})
        target  = ab_data.get("target", "single_enemy")

        action_type = "spell" if phase == BattlePhase.SELECT_SPELL else "item"

        # single-target: open target selector
        if target == "single_enemy":
            self._target_pool = self._state.alive_enemies()
            self._target_sel  = 0
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        elif target == "single_ally":
            self._target_pool = self._state.alive_party()
            self._target_sel  = 0
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        elif target == "single_ko":
            pool = self._state.ko_party()
            if not pool:
                return
            self._target_pool = pool
            self._target_sel  = 0
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        # AoE: resolve immediately
        elif target in ("all_allies", "party"):
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": self._state.alive_party(),
            }
            self._resolve_action()
        elif target in ("all_enemies", "group_enemies"):
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": self._state.alive_enemies(),
            }
            self._resolve_action()
        elif target == "self":
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": [active],
            }
            self._resolve_action()
        else:
            self._state.pending_action = {
                "type": action_type, "data": ab_data, "source": active,
                "targets": self._state.alive_enemies(),
            }
            self._resolve_action()

    def _handle_target(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._sub_items.clear()
            return

        if key in (pygame.K_LEFT, pygame.K_UP):
            self._target_sel = max(0, self._target_sel - 1)
        elif key in (pygame.K_RIGHT, pygame.K_DOWN):
            self._target_sel = min(len(self._target_pool) - 1, self._target_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._target_pool:
                self._state.pending_action["targets"] = [self._target_pool[self._target_sel]]
                self._resolve_action()

    # ── Action resolution ─────────────────────────────────────

    def _resolve_action(self) -> None:
        action = self._state.pending_action
        if not action:
            return
        source = action.get("source")
        targets = action.get("targets", [])
        atype = action.get("type", "attack")
        msg_parts: list[str] = []

        for target in targets:
            if atype == "attack":
                dmg = max(1, source.atk - target.def_)
                actual = target.apply_damage(dmg)
                self._state.add_float(str(actual), *self._float_pos(target), C_DMG_PHYS)
                msg_parts.append(f"{source.name} attacked {target.name} for {actual} damage!")
            elif atype == "spell":
                ab = action.get("data", {})
                spell_type = ab.get("type", "spell")
                coeff = ab.get("spell_coeff") or ab.get("heal_coeff") or 1.0
                spell_name = ab.get("name", "Spell")

                # deduct MP once (first target only)
                if source and target == targets[0]:
                    source.mp = max(0, source.mp - ab.get("mp_cost", 0))

                if spell_type == "heal" and ab.get("revive_hp_pct"):
                    if target.is_ko:
                        pct = ab["revive_hp_pct"]
                        target.hp = max(1, int(target.hp_max * pct))
                        target.is_ko = False
                        self._state.add_float("Revive", *self._float_pos(target), C_HEAL)
                        msg_parts.append(f"{source.name} casts {spell_name}! {target.name} revived!")
                elif spell_type == "heal":
                    amount = int(source.mres * coeff) if source else 10
                    actual = target.apply_heal(amount)
                    self._state.add_float(str(actual), *self._float_pos(target), C_HEAL)
                    msg_parts.append(f"{source.name} casts {spell_name}! {target.name} healed {actual} HP!")
                elif spell_type == "utility":
                    target.clear_all_status()
                    self._state.add_float("Cured", *self._float_pos(target), C_HEAL)
                    msg_parts.append(f"{source.name} casts {spell_name}! {target.name} cured!")
                elif spell_type == "buff":
                    self._state.add_float("Buff", *self._float_pos(target), C_HEAL)
                    msg_parts.append(f"{source.name} casts {spell_name} on {target.name}!")
                elif spell_type == "debuff":
                    self._state.add_float("Debuff", *self._float_pos(target), C_DMG_MAGIC)
                    msg_parts.append(f"{source.name} casts {spell_name} on {target.name}!")
                else:
                    dmg = max(1, int(source.mres * coeff) - target.def_) if source else 10
                    actual = target.apply_damage(dmg)
                    self._state.add_float(str(actual), *self._float_pos(target), C_DMG_MAGIC)
                    msg_parts.append(f"{source.name} casts {spell_name}! {actual} damage to {target.name}!")
            elif atype == "item":
                actual = target.apply_heal(100)
                self._state.add_float(str(actual), *self._float_pos(target), C_HEAL)
                msg_parts.append(f"{source.name} used item on {target.name}! Healed {actual} HP!")

        self._state.pending_action = None
        self._enter_resolve(msg_parts[0] if msg_parts else "")

    def _enter_resolve(self, msg: str) -> None:
        self._resolve_msg = msg
        self._resolve_timer = 3.0
        self._state.phase = BattlePhase.RESOLVE

    def _check_result(self) -> None:
        print(f"[DEBUG] _check_result called | phase={self._state.phase} | active={self._state.active.name if self._state.active else None}")
        if self._state.enemies_wiped:
            self._handle_victory()
            return
        if self._state.party_wiped:
            self._handle_defeat()
            return

        self._state.advance_turn()
        active = self._state.active

        if active and active.is_enemy:
            self._state.phase = BattlePhase.ENEMY_TURN
            self._resolve_enemy_turn()
        else:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._cmd_sel = 0

    def _resolve_enemy_turn(self) -> None:
        active = self._state.active
        if not active or not active.is_enemy:
            self._check_result()
            return

        targets = self._state.alive_party()
        if not targets:
            self._check_result()
            return

        target = random.choice(targets)

        dmg = max(1, active.atk - target.def_)
        actual = target.apply_damage(dmg)

        self._state.add_float(str(actual), *self._float_pos(target), C_DMG_PHYS)
        self._enter_resolve(f"{active.name} attacked {target.name} for {actual} damage!")

    def _attempt_run(self) -> None:
        """Stub — always succeeds. Real flee formula Phase 4."""
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Victory ───────────────────────────────────────────────

    def _handle_victory(self) -> None:
        self._state.phase = BattlePhase.POST_BATTLE
        game_state = self._holder.get()

        # set boss flag
        if self._boss_flag:
            game_state.flags.add_flag(self._boss_flag)

        # calculate EXP + loot
        rewards = self._reward_calc.calculate(
            enemies=self._state.enemies,
            party=game_state.party,
            boss_flag=self._boss_flag,
        )

        # sync HP/MP from combatants back to MemberState
        self._sync_party_state(game_state.party)

        # add MC drops to repository
        EncounterManager.add_mc_drops(game_state.repository, rewards.loot.mc_drops)

        # launch post-battle screen
        self._scene_manager.switch(PostBattleScene(
            rewards=rewards,
            scene_manager=self._scene_manager,
            registry=self._registry,
            on_continue=self._return_to_world_map,
        ))

    def _handle_defeat(self) -> None:
        """Stub — Game Over screen Phase 4 follow-up."""
        self._state.phase = BattlePhase.GAME_OVER
        self._scene_manager.switch(self._registry.get("world_map"))

    def _sync_party_state(self, party) -> None:
        """Write surviving HP/MP from Combatants back to MemberState."""
        combatant_map = {c.id: c for c in self._state.party}
        for member in party.members:
            c = combatant_map.get(member.id)
            if c is None:
                continue
            member.hp = c.hp
            member.mp = c.mp
            if c.is_ko:
                member.hp = 0

    def _return_to_world_map(self) -> None:
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        self._state.update_floats(delta)
        if self._state.phase == BattlePhase.RESOLVE:
            self._resolve_timer -= delta
            if self._resolve_timer <= 0:
                self._resolve_msg = ""
                self._check_result()
        elif self._state.phase == BattlePhase.ENEMY_TURN:
            self._resolve_enemy_turn()

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        screen.fill(C_BG)
        self._draw_enemy_area(screen)
        self._draw_action_message(screen)
        self._draw_bottom_panel(screen)
        self._draw_damage_floats(screen)

    def _draw_action_message(self, screen: pygame.Surface) -> None:
        if not self._resolve_msg:
            return
        msg_h = 28
        msg_y = ENEMY_AREA_H - msg_h
        bg = pygame.Surface((Settings.SCREEN_WIDTH, msg_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        screen.blit(bg, (0, msg_y))
        text = self._font_cmd.render(self._resolve_msg, True, C_TEXT)
        screen.blit(text, (Settings.SCREEN_WIDTH // 2 - text.get_width() // 2, msg_y + 6))

    # ── Enemy area ────────────────────────────────────────────

    def _draw_enemy_area(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, C_FLOOR,
                         (0, ENEMY_AREA_H - 60, Settings.SCREEN_WIDTH, 60))
        pygame.draw.line(screen, (42, 42, 68),
                         (0, ENEMY_AREA_H - 60), (Settings.SCREEN_WIDTH, ENEMY_AREA_H - 60))

        enemies = self._state.enemies
        n = len(enemies)
        offsets = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])
        cx = Settings.SCREEN_WIDTH // 2
        cy = ENEMY_AREA_H // 2 + 10

        for i, enemy in enumerate(enemies):
            ox, oy = offsets[i]
            self._draw_enemy(screen, enemy, cx + ox, cy + oy, i)

    def _draw_enemy(self, screen: pygame.Surface, enemy: Combatant,
                    cx: int, cy: int, index: int) -> None:
        w, h = self._enemy_rect_size(enemy)
        rx, ry = cx - w // 2, cy - h // 2

        base_col = (30, 30, 40) if enemy.is_ko else (42, 58, 90)
        bdr_col  = (50, 50, 60) if enemy.is_ko else (74, 106, 154)
        pygame.draw.rect(screen, base_col, (rx, ry, w, h), border_radius=4)
        pygame.draw.rect(screen, bdr_col,  (rx, ry, w, h), 1, border_radius=4)

        name_surf = self._font_enemy.render(enemy.name, True, C_TEXT_MUT)
        screen.blit(name_surf, (cx - name_surf.get_width() // 2, ry + h + 4))

        bar_w = w
        bar_x = cx - bar_w // 2
        bar_y = ry + h + 4 + name_surf.get_height() + 3
        pygame.draw.rect(screen, (42, 42, 42), (bar_x, bar_y, bar_w, 5), border_radius=2)
        hp_fill = int(bar_w * enemy.hp_pct)
        hp_col  = C_HP_OK if enemy.hp_pct > HP_LOW_THRESHOLD else C_HP_LOW
        if hp_fill > 0 and not enemy.is_ko:
            pygame.draw.rect(screen, hp_col, (bar_x, bar_y, hp_fill, 5), border_radius=2)

        if (self._state.phase == BattlePhase.SELECT_TARGET
                and self._target_pool
                and index < len(self._target_pool)
                and self._target_pool[self._target_sel] is enemy):
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, ry - 2, w + 4, h + 4), 2, border_radius=5)

    # ── Bottom panel ──────────────────────────────────────────

    def _draw_bottom_panel(self, screen: pygame.Surface) -> None:
        pygame.draw.line(screen, C_PANEL_LINE,
                         (0, ENEMY_AREA_H), (Settings.SCREEN_WIDTH, ENEMY_AREA_H))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (PARTY_W, ENEMY_AREA_H), (PARTY_W, Settings.SCREEN_HEIGHT))
        self._draw_party_panel(screen)
        self._draw_command_panel(screen)

    def _draw_party_panel(self, screen: pygame.Surface) -> None:
        panel_y = ENEMY_AREA_H + 8
        for i, member in enumerate(self._state.party):
            self._draw_party_row(screen, member, panel_y + i * (ROW_H + 2))

    def _draw_party_row(self, screen: pygame.Surface,
                        member: Combatant, y: int) -> None:
        active    = self._state.active
        is_active = active is not None and active is member and not member.is_enemy
        is_target = (self._state.phase == BattlePhase.SELECT_TARGET
                     and self._target_pool
                     and self._target_sel < len(self._target_pool)
                     and self._target_pool[self._target_sel] is member)
        bg  = C_ROW_ACTIVE if is_active else C_ROW_NORMAL
        bdr = C_BORDER_ACT if is_active else C_BORDER_NORM

        rx, rw = ROW_PAD, PARTY_W - ROW_PAD * 2
        pygame.draw.rect(screen, bg,  (rx, y, rw, ROW_H - 2), border_radius=4)
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H - 2), 1, border_radius=4)
        if is_target:
            pygame.draw.rect(screen, (204, 170, 255),
                             (rx - 2, y - 2, rw + 4, ROW_H + 2), 2, border_radius=5)

        px = rx + 6
        py = y + (ROW_H - 2 - PORTRAIT_SIZE) // 2
        img = self._load_portrait(member.id)
        if img:
            screen.blit(img, (px, py))
        else:
            col = (58, 42, 42) if is_active else (42, 42, 58)
            pygame.draw.rect(screen, col, (px, py, PORTRAIT_SIZE, PORTRAIT_SIZE), border_radius=3)
            init = "".join(w[0].upper() for w in member.name.split()[:2])
            s = self._font_badge.render(init, True, C_TEXT_MUT)
            screen.blit(s, (px + PORTRAIT_SIZE // 2 - s.get_width() // 2,
                             py + PORTRAIT_SIZE // 2 - s.get_height() // 2))

        if member.status_effects:
            effect = member.status_effects[0]
            if effect in STATUS_COLORS:
                bg_col, text_col, label = STATUS_COLORS[effect]
                bs = self._font_badge.render(label, True, text_col)
                bx = px + PORTRAIT_SIZE - bs.get_width() - 2
                pygame.draw.rect(screen, bg_col,
                                 (bx - 3, py - 7, bs.get_width() + 6, bs.get_height() + 2),
                                 border_radius=2)
                screen.blit(bs, (bx, py - 6))

        if member.is_ko:
            ko_surf = pygame.Surface((PORTRAIT_SIZE, PORTRAIT_SIZE), pygame.SRCALPHA)
            ko_surf.fill((0, 0, 0, 160))
            screen.blit(ko_surf, (px, py))

        sx = px + PORTRAIT_SIZE + 8
        sw = rw - PORTRAIT_SIZE - 20
        bx = sx + 22
        bw = sw - 22 - 50

        screen.blit(self._font_name.render(
            member.name, True, C_TEXT if not member.is_ko else C_TEXT_DIM), (sx, y + 5))

        hp_pct  = member.hp_pct
        hp_col  = C_HP_LOW  if hp_pct <= HP_LOW_THRESHOLD else C_HP_OK
        hp_lcol = C_HP_LABEL_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_LABEL_OK
        screen.blit(self._font_stat.render("HP", True, hp_lcol), (sx, y + 20))
        pygame.draw.rect(screen, (42, 42, 42), (bx, y + 20, bw, BAR_H), border_radius=2)
        if not member.is_ko:
            pygame.draw.rect(screen, hp_col, (bx, y + 20, int(bw * hp_pct), BAR_H), border_radius=2)
        screen.blit(self._font_stat.render(f"{member.hp}/{member.hp_max}", True, hp_lcol),
                    (bx + bw + 4, y + 19))

        if member.mp_max > 0:
            mp_pct = member.mp / member.mp_max
            screen.blit(self._font_stat.render("MP", True, C_MP_LABEL), (sx, y + 32))
            pygame.draw.rect(screen, (42, 42, 42), (bx, y + 32, bw, BAR_H), border_radius=2)
            pygame.draw.rect(screen, C_MP, (bx, y + 32, int(bw * mp_pct), BAR_H), border_radius=2)
            screen.blit(self._font_stat.render(f"{member.mp}/{member.mp_max}", True, C_MP_LABEL),
                        (bx + bw + 4, y + 31))

    # ── Command panel ─────────────────────────────────────────

    def _draw_command_panel(self, screen: pygame.Surface) -> None:
        panel_x = PARTY_W + 20
        active  = self._state.active
        phase   = self._state.phase

        screen.blit(self._font_turn.render(
            f"{active.name}'s turn" if active else "", True, C_TEXT_MUT),
            (panel_x, ENEMY_AREA_H + 10))

        if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
            self._draw_submenu(screen, panel_x, ENEMY_AREA_H + 30)
        elif phase == BattlePhase.SELECT_TARGET:
            action = self._state.pending_action
            label = action.get("data", {}).get("name", "Attack") if action else "Attack"
            screen.blit(self._font_name.render(
                f"Select target for {label}", True, (204, 170, 255)),
                (panel_x, ENEMY_AREA_H + 34))
            screen.blit(self._font_stat.render(
                "↑↓ choose · ENTER confirm · ESC cancel", True, C_TEXT_MUT),
                (panel_x, ENEMY_AREA_H + 56))
        else:
            self._draw_main_cmd(screen, panel_x, ENEMY_AREA_H + 30, active)

    def _draw_main_cmd(self, screen: pygame.Surface,
                       x: int, y: int, active: Combatant | None) -> None:
        for i, label in enumerate(self._cmd_items):
            sel      = (i == self._cmd_sel)
            disabled = (label == "Spell" and active is not None and active.mp_max == 0)
            row_y    = y + i * 36

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 4, CMD_W - 30, 32), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 4, CMD_W - 30, 32), 1, border_radius=4)

            col = (C_TEXT_DIM if disabled
                   else (200, 160, 255) if sel else C_TEXT_MUT)

            if sel and not disabled:
                screen.blit(self._font_cmd.render("▶", True, (200, 160, 255)), (x - 16, row_y))
            screen.blit(self._font_cmd.render(label, True, col), (x, row_y))

            if label == "Spell" and disabled:
                screen.blit(self._font_stat.render("—", True, C_TEXT_DIM), (x + 60, row_y + 2))
            elif label in ("Item", "Spell") and not disabled:
                screen.blit(self._font_stat.render("→", True, C_TEXT_DIM), (x + 60, row_y + 2))

    def _draw_submenu(self, screen: pygame.Surface, x: int, y: int) -> None:
        for i, item in enumerate(self._sub_items):
            sel      = (i == self._sub_sel)
            disabled = item.get("disabled", False)
            row_y    = y + i * 28

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 3, CMD_W - 30, 26), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 3, CMD_W - 30, 26), 1, border_radius=4)

            col = C_TEXT_DIM if disabled else (C_TEXT if sel else C_TEXT_MUT)
            if sel and not disabled:
                screen.blit(self._font_sub.render("▶", True, (200, 160, 255)), (x - 14, row_y))
            screen.blit(self._font_sub.render(item["label"], True, col), (x, row_y))

            if "mp_cost" in item:
                screen.blit(self._font_stat.render(
                    f"MP {item['mp_cost']}", True,
                    C_TEXT_DIM if disabled else C_MP_LABEL), (x + 160, row_y + 1))
            elif "qty" in item:
                screen.blit(self._font_stat.render(
                    f"×{item['qty']}", True, C_TEXT_MUT), (x + 160, row_y + 1))

        screen.blit(self._font_stat.render("ESC back", True, C_TEXT_DIM),
                    (x, y + len(self._sub_items) * 28 + 8))

    # ── Damage floats ─────────────────────────────────────────

    def _draw_damage_floats(self, screen: pygame.Surface) -> None:
        for f in self._state.damage_floats:
            surf = self._font_dmg.render(f.text, True, f.color)
            surf.set_alpha(f.alpha)
            screen.blit(surf, (f.x, f.y))

    # ── Float position ────────────────────────────────────────

    def _float_pos(self, combatant: Combatant) -> tuple[int, int]:
        if combatant.is_enemy:
            n = len(self._state.enemies)
            idx = self._state.enemies.index(combatant)
            ox, oy = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])[idx]
            cx = Settings.SCREEN_WIDTH // 2 + ox
            cy = ENEMY_AREA_H // 2 + 10 + oy
            _, h = self._enemy_rect_size(combatant)
            return cx - 15, cy - h // 2 - 30
        else:
            idx = self._state.party.index(combatant)
            return PARTY_W - 60, ENEMY_AREA_H + 8 + idx * (ROW_H + 2) + 5
