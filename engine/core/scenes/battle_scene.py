# engine/core/scenes/battle_scene.py
#
# Phase 4 — Battle system

from __future__ import annotations

import pygame
from pathlib import Path

from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager
from engine.core.scene_registry import SceneRegistry
from engine.core.settings import Settings
from engine.core.battle.combatant import Combatant, StatusEffect
from engine.core.battle.battle_state import BattleState, BattlePhase

# ── Layout ────────────────────────────────────────────────────
ENEMY_AREA_H    = int(Settings.SCREEN_HEIGHT * 0.65)   # ~469px
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
C_ENEMY_BG     = (13,  13,  26)
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
C_HP_CRIT      = (204, 68,  68)
C_MP           = (68,  102, 204)
C_HP_LABEL_OK  = (136, 204, 136)
C_HP_LABEL_LOW = (204, 136, 136)
C_MP_LABEL     = (136, 136, 204)
C_DMG_PHYS     = (255, 180, 80)
C_DMG_MAGIC    = (140, 180, 255)
C_HEAL         = (100, 220, 100)
C_MISS         = (180, 180, 180)

HP_LOW_THRESHOLD  = 0.35
HP_CRIT_THRESHOLD = 0.15

ENEMY_LAYOUTS = {
    1: [(0,   0)],
    2: [(-80, 0),  (80,  0)],
    3: [(-110, -30), (0, 20), (110, -20)],
    4: [(-140, -20), (-45, 20), (45, -20), (140, 20)],
    5: [(-160, -30), (-80, 20), (0, -10), (80, 20), (160, -30)],
}

ENEMY_SIZES = {
    "boss": (96, 96),
    "large": (80, 80),
    "medium": (64, 64),
    "small": (52, 52),
}


class BattleScene(Scene):
    """
    Phase 4 — renders the battle screen and handles player input.
    Enemy AI resolution: stub — Phase 4 follow-up.
    Post-battle EXP/loot screen: stub — Phase 4 follow-up.
    """

    def __init__(
        self,
        battle_state: BattleState,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        scenario_path: str = "",
        on_victory: callable | None = None,
        on_defeat: callable | None = None,
    ) -> None:
        self._state = battle_state
        self._scene_manager = scene_manager
        self._registry = registry
        self._scenario_path = Path(scenario_path)
        self._on_victory = on_victory or (lambda: None)
        self._on_defeat = on_defeat or (lambda: None)

        self._fonts_ready = False
        self._portraits: dict[str, pygame.Surface] = {}

        # command menu
        self._cmd_items: list[str] = ["Attack", "Spell", "Item", "Run"]
        self._cmd_sel: int = 0

        # spell/item submenu
        self._sub_items: list[dict] = []   # {label, data, disabled}
        self._sub_sel: int = 0

        # target selection
        self._target_pool: list[Combatant] = []
        self._target_sel: int = 0

        # enemy sprite size hints — stub, keyed by combatant id
        self._enemy_size: dict[str, tuple] = {}

        self._state.build_turn_order()

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
        # vary by name length as a stub heuristic
        idx = len(enemy.name) % 3
        return [ENEMY_SIZES["medium"], ENEMY_SIZES["small"], ENEMY_SIZES["medium"]][idx]

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        phase = self._state.phase
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if phase == BattlePhase.PLAYER_TURN:
                self._handle_cmd(event.key)
            elif phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
                self._handle_sub(event.key)
            elif phase == BattlePhase.SELECT_TARGET:
                self._handle_target(event.key)

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
        elif key == pygame.K_ESCAPE:
            pass   # no-op at top level

    def _confirm_cmd(self) -> None:
        label = self._cmd_items[self._cmd_sel]
        active = self._state.active
        if label == "Attack":
            self._target_pool = self._state.alive_enemies()
            self._target_sel = 0
            self._state.pending_action = {"type": "attack", "source": active}
            self._state.phase = BattlePhase.SELECT_TARGET
        elif label == "Spell":
            if active and active.mp_max > 0:
                self._open_spell_menu(active)
        elif label == "Item":
            self._open_item_menu()
        elif label == "Run":
            self._attempt_run()   # stub — Phase 4

    def _open_spell_menu(self, active: Combatant) -> None:
        self._sub_items = []
        for ab in active.abilities:
            if ab.get("type") not in ("spell", "heal", "buff", "debuff", "utility"):
                continue
            cost = ab.get("mp_cost", 0)
            disabled = active.mp < cost
            self._sub_items.append({
                "label":    ab["name"],
                "mp_cost":  cost,
                "data":     ab,
                "disabled": disabled,
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
        if key == pygame.K_ESCAPE or key == pygame.K_LEFT:
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
        item = self._sub_items[self._sub_sel]
        if item.get("disabled"):
            return
        active = self._state.active
        phase = self._state.phase
        ab_data = item.get("data", {})

        # determine target pool
        target = ab_data.get("target", "single_enemy")
        if target in ("single_enemy",):
            self._target_pool = self._state.alive_enemies()
            self._target_sel = 0
            self._state.pending_action = {
                "type": "spell" if phase == BattlePhase.SELECT_SPELL else "item",
                "data": ab_data,
                "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        elif target in ("single_ally",):
            self._target_pool = self._state.alive_party()
            self._target_sel = 0
            self._state.pending_action = {
                "type": "spell" if phase == BattlePhase.SELECT_SPELL else "item",
                "data": ab_data,
                "source": active,
            }
            self._state.phase = BattlePhase.SELECT_TARGET
        else:
            # AoE — no target selection needed, resolve directly
            self._state.pending_action = {
                "type": "spell" if phase == BattlePhase.SELECT_SPELL else "item",
                "data": ab_data,
                "source": active,
                "targets": self._state.alive_enemies(),
            }
            self._resolve_action()

    def _handle_target(self, key: int) -> None:
        if key == pygame.K_ESCAPE or key == pygame.K_LEFT:
            self._state.phase = BattlePhase.PLAYER_TURN
            return
        if key in (pygame.K_LEFT, pygame.K_UP):
            self._target_sel = max(0, self._target_sel - 1)
        elif key in (pygame.K_RIGHT, pygame.K_DOWN):
            self._target_sel = min(len(self._target_pool) - 1, self._target_sel + 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._target_pool:
                target = self._target_pool[self._target_sel]
                self._state.pending_action["targets"] = [target]
                self._resolve_action()

    # ── Action resolution (stub) ──────────────────────────────

    def _resolve_action(self) -> None:
        """
        Stub resolver — applies flat damage/heal for now.
        Full formula (str, int, coeff, crit, row) in Phase 4 follow-up.
        """
        action = self._state.pending_action
        if not action:
            return

        source  = action.get("source")
        targets = action.get("targets", [])
        atype   = action.get("type", "attack")

        for target in targets:
            if atype == "attack":
                dmg = max(1, source.atk - target.def_)
                actual = target.apply_damage(dmg)
                self._state.add_float(str(actual), *self._combatant_float_pos(target), C_DMG_PHYS)
            elif atype == "spell":
                ab = action.get("data", {})
                coeff = ab.get("spell_coeff") or ab.get("heal_coeff") or 1.0
                mp_cost = ab.get("mp_cost", 0)
                if source:
                    source.mp = max(0, source.mp - mp_cost)
                if ab.get("type") == "heal":
                    amount = int(source.int_ * coeff) if source else 10
                    actual = target.apply_heal(amount)
                    self._state.add_float(str(actual), *self._combatant_float_pos(target), C_HEAL)
                else:
                    dmg = max(1, int(source.int_ * coeff) - target.mres) if source else 10
                    actual = target.apply_damage(dmg)
                    self._state.add_float(str(actual), *self._combatant_float_pos(target), C_DMG_MAGIC)
            elif atype == "item":
                # stub — flat 100 HP restore
                actual = target.apply_heal(100)
                self._state.add_float(str(actual), *self._combatant_float_pos(target), C_HEAL)

        self._state.pending_action = None
        self._check_result()

    def _check_result(self) -> None:
        if self._state.enemies_wiped:
            self._state.phase = BattlePhase.POST_BATTLE
            self._state.message = "Victory!"
            self._on_victory()
            return
        if self._state.party_wiped:
            self._state.phase = BattlePhase.GAME_OVER
            self._state.message = "Defeated..."
            self._on_defeat()
            return
        self._state.advance_turn()
        active = self._state.active
        if active and active.is_enemy:
            self._state.phase = BattlePhase.ENEMY_TURN
            self._resolve_enemy_turn()   # stub
        else:
            self._state.phase = BattlePhase.PLAYER_TURN
            self._cmd_sel = 0

    def _resolve_enemy_turn(self) -> None:
        """Stub — flat attack on random alive party member. Full AI in Phase 4."""
        import random
        active = self._state.active
        targets = self._state.alive_party()
        if active and targets:
            target = random.choice(targets)
            dmg = max(1, active.atk - target.def_)
            actual = target.apply_damage(dmg)
            self._state.message = f"{active.name} attacks {target.name}!"
            self._state.add_float(str(actual), *self._combatant_float_pos(target), C_DMG_PHYS)
        self._check_result()

    def _attempt_run(self) -> None:
        """Stub — always succeeds for now. Real flee formula in Phase 4."""
        self._scene_manager.switch(self._registry.get("world_map"))

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        self._state.update_floats(delta)

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        screen.fill(C_BG)
        self._draw_enemy_area(screen)
        self._draw_bottom_panel(screen)
        self._draw_damage_floats(screen)

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
            ex = cx + ox
            ey = cy + oy
            self._draw_enemy(screen, enemy, ex, ey, i)

    def _draw_enemy(self, screen: pygame.Surface, enemy: Combatant,
                    cx: int, cy: int, index: int) -> None:
        w, h = self._enemy_rect_size(enemy)
        rect_x = cx - w // 2
        rect_y = cy - h // 2

        # dim if KO
        alpha_mod = 80 if enemy.is_ko else 255

        # sprite placeholder rect
        base_col = (42, 58, 90) if not enemy.is_enemy else (42, 58, 90)
        bdr_col  = (74, 106, 154)
        if enemy.is_ko:
            base_col = (30, 30, 40)
            bdr_col  = (50, 50, 60)
        pygame.draw.rect(screen, base_col, (rect_x, rect_y, w, h), border_radius=4)
        pygame.draw.rect(screen, bdr_col,  (rect_x, rect_y, w, h), 1, border_radius=4)

        # enemy name label
        name_surf = self._font_enemy.render(enemy.name, True, C_TEXT_MUT)
        nx = cx - name_surf.get_width() // 2
        ny = rect_y + rect_y + h - rect_y + 4   # just below sprite
        screen.blit(name_surf, (cx - name_surf.get_width() // 2, rect_y + h + 4))

        # HP bar under name
        bar_w = w
        bar_x = cx - bar_w // 2
        bar_y = rect_y + h + 4 + name_surf.get_height() + 3
        pygame.draw.rect(screen, (42, 42, 42), (bar_x, bar_y, bar_w, 5), border_radius=2)
        hp_fill = int(bar_w * enemy.hp_pct)
        hp_col = C_HP_OK if enemy.hp_pct > HP_LOW_THRESHOLD else C_HP_LOW
        if hp_fill > 0:
            pygame.draw.rect(screen, hp_col, (bar_x, bar_y, hp_fill, 5), border_radius=2)

        # target cursor
        if (self._state.phase == BattlePhase.SELECT_TARGET
                and self._target_pool
                and index < len(self._target_pool)
                and self._target_pool[self._target_sel] is enemy):
            pygame.draw.rect(screen, (204, 170, 255),
                             (rect_x - 2, rect_y - 2, w + 4, h + 4), 2, border_radius=5)

    # ── Bottom panel ──────────────────────────────────────────

    def _draw_bottom_panel(self, screen: pygame.Surface) -> None:
        pygame.draw.line(screen, C_PANEL_LINE,
                         (0, ENEMY_AREA_H), (Settings.SCREEN_WIDTH, ENEMY_AREA_H))
        pygame.draw.line(screen, C_PANEL_LINE,
                         (PARTY_W, ENEMY_AREA_H), (PARTY_W, Settings.SCREEN_HEIGHT))

        self._draw_party_panel(screen)
        self._draw_command_panel(screen)

    # ── Party panel ───────────────────────────────────────────

    def _draw_party_panel(self, screen: pygame.Surface) -> None:
        panel_y = ENEMY_AREA_H + 8
        for i, member in enumerate(self._state.party):
            row_y = panel_y + i * (ROW_H + 2)
            self._draw_party_row(screen, member, row_y)

    def _draw_party_row(self, screen: pygame.Surface,
                        member: Combatant, y: int) -> None:
        active = self._state.active
        is_active = (active is not None and active is member
                     and not member.is_enemy)
        bg  = C_ROW_ACTIVE  if is_active else C_ROW_NORMAL
        bdr = C_BORDER_ACT  if is_active else C_BORDER_NORM

        rx = ROW_PAD
        rw = PARTY_W - ROW_PAD * 2
        pygame.draw.rect(screen, bg,  (rx, y, rw, ROW_H - 2), border_radius=4)
        pygame.draw.rect(screen, bdr, (rx, y, rw, ROW_H - 2), 1, border_radius=4)

        # portrait
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

        # status badge — top-right of portrait
        if member.status_effects:
            effect = member.status_effects[0]
            if effect in STATUS_COLORS:
                bg_col, text_col, label = STATUS_COLORS[effect]
                bs = self._font_badge.render(label, True, text_col)
                bx = px + PORTRAIT_SIZE - bs.get_width() - 2
                by = py - 6
                pygame.draw.rect(screen, bg_col,
                                 (bx - 3, by - 1, bs.get_width() + 6, bs.get_height() + 2),
                                 border_radius=2)
                screen.blit(bs, (bx, by))

        # KO overlay
        if member.is_ko:
            ko_surf = pygame.Surface((PORTRAIT_SIZE, PORTRAIT_SIZE), pygame.SRCALPHA)
            ko_surf.fill((0, 0, 0, 160))
            screen.blit(ko_surf, (px, py))

        # stats area
        sx = px + PORTRAIT_SIZE + 8
        sw = rw - PORTRAIT_SIZE - 20
        name_y = y + 5
        bar_y1 = y + 20
        bar_y2 = y + 32

        # name
        name_s = self._font_name.render(member.name, True, C_TEXT if not member.is_ko else C_TEXT_DIM)
        screen.blit(name_s, (sx, name_y))

        # HP bar row
        hp_pct = member.hp_pct
        hp_col   = C_HP_LOW  if hp_pct <= HP_LOW_THRESHOLD  else C_HP_OK
        hp_lcol  = C_HP_LABEL_LOW if hp_pct <= HP_LOW_THRESHOLD else C_HP_LABEL_OK
        hp_label = self._font_stat.render("HP", True, hp_lcol)
        screen.blit(hp_label, (sx, bar_y1 - 1))
        bx = sx + 22
        bw = sw - 22 - 50
        pygame.draw.rect(screen, (42, 42, 42), (bx, bar_y1, bw, BAR_H), border_radius=2)
        if not member.is_ko:
            pygame.draw.rect(screen, hp_col, (bx, bar_y1, int(bw * hp_pct), BAR_H), border_radius=2)
        hp_val = self._font_stat.render(f"{member.hp}/{member.hp_max}", True, hp_lcol)
        screen.blit(hp_val, (bx + bw + 4, bar_y1 - 1))

        # MP bar row
        if member.mp_max > 0:
            mp_pct = member.mp / member.mp_max
            mp_label = self._font_stat.render("MP", True, C_MP_LABEL)
            screen.blit(mp_label, (sx, bar_y2 - 1))
            pygame.draw.rect(screen, (42, 42, 42), (bx, bar_y2, bw, BAR_H), border_radius=2)
            pygame.draw.rect(screen, C_MP, (bx, bar_y2, int(bw * mp_pct), BAR_H), border_radius=2)
            mp_val = self._font_stat.render(f"{member.mp}/{member.mp_max}", True, C_MP_LABEL)
            screen.blit(mp_val, (bx + bw + 4, bar_y2 - 1))

    # ── Command panel ─────────────────────────────────────────

    def _draw_command_panel(self, screen: pygame.Surface) -> None:
        panel_x = PARTY_W + 20
        active = self._state.active

        # whose turn label
        turn_name = active.name if active else ""
        turn_s = self._font_turn.render(f"{turn_name}'s turn", True, C_TEXT_MUT)
        screen.blit(turn_s, (panel_x, ENEMY_AREA_H + 10))

        phase = self._state.phase

        if phase in (BattlePhase.SELECT_SPELL, BattlePhase.SELECT_ITEM):
            self._draw_submenu(screen, panel_x, ENEMY_AREA_H + 30)
        elif phase == BattlePhase.POST_BATTLE:
            msg = self._font_cmd.render(self._state.message, True, (100, 220, 100))
            screen.blit(msg, (panel_x, ENEMY_AREA_H + 50))
        elif phase == BattlePhase.GAME_OVER:
            msg = self._font_cmd.render(self._state.message, True, C_HP_LOW)
            screen.blit(msg, (panel_x, ENEMY_AREA_H + 50))
        else:
            self._draw_main_cmd(screen, panel_x, ENEMY_AREA_H + 30, active)

        # bottom message
        if self._state.message and phase not in (BattlePhase.POST_BATTLE, BattlePhase.GAME_OVER):
            msg_s = self._font_msg.render(self._state.message, True, C_TEXT_MUT)
            screen.blit(msg_s, (panel_x, Settings.SCREEN_HEIGHT - 20))

    def _draw_main_cmd(self, screen: pygame.Surface,
                       x: int, y: int, active: Combatant | None) -> None:
        for i, label in enumerate(self._cmd_items):
            sel = (i == self._cmd_sel)
            row_y = y + i * 36

            # gray out Spell if no mp_max
            disabled = (label == "Spell" and active is not None and active.mp_max == 0)

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 4, CMD_W - 30, 32), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 4, CMD_W - 30, 32), 1, border_radius=4)

            cur_col = (C_TEXT_DIM if disabled
                       else (200, 160, 255) if sel
                       else C_TEXT_MUT)

            if sel and not disabled:
                cur = self._font_cmd.render("▶", True, (200, 160, 255))
                screen.blit(cur, (x - 16, row_y))

            txt = self._font_cmd.render(label, True, cur_col)
            screen.blit(txt, (x, row_y))

            if label == "Spell" and disabled:
                dash = self._font_stat.render("—", True, C_TEXT_DIM)
                screen.blit(dash, (x + txt.get_width() + 8, row_y + 2))
            elif label in ("Item", "Spell") and not disabled:
                arrow = self._font_stat.render("→", True, C_TEXT_DIM)
                screen.blit(arrow, (x + txt.get_width() + 8, row_y + 2))

    def _draw_submenu(self, screen: pygame.Surface, x: int, y: int) -> None:
        for i, item in enumerate(self._sub_items):
            sel = (i == self._sub_sel)
            row_y = y + i * 28
            disabled = item.get("disabled", False)

            if sel and not disabled:
                pygame.draw.rect(screen, C_CMD_SEL_BG,
                                 (x - 4, row_y - 3, CMD_W - 30, 26), border_radius=4)
                pygame.draw.rect(screen, C_CMD_SEL_BDR,
                                 (x - 4, row_y - 3, CMD_W - 30, 26), 1, border_radius=4)

            col = C_TEXT_DIM if disabled else (C_TEXT if sel else C_TEXT_MUT)

            if sel and not disabled:
                cur = self._font_sub.render("▶", True, (200, 160, 255))
                screen.blit(cur, (x - 14, row_y))

            label = item["label"]
            ls = self._font_sub.render(label, True, col)
            screen.blit(ls, (x, row_y))

            # MP cost or qty
            if "mp_cost" in item:
                cost_s = self._font_stat.render(f"MP {item['mp_cost']}", True,
                                                 C_TEXT_DIM if disabled else C_MP_LABEL)
                screen.blit(cost_s, (x + 160, row_y + 1))
            elif "qty" in item:
                qty_s = self._font_stat.render(f"×{item['qty']}", True, C_TEXT_MUT)
                screen.blit(qty_s, (x + 160, row_y + 1))

        # back hint
        back = self._font_stat.render("ESC back", True, C_TEXT_DIM)
        screen.blit(back, (x, y + len(self._sub_items) * 28 + 8))

    # ── Damage floats ─────────────────────────────────────────

    def _draw_damage_floats(self, screen: pygame.Surface) -> None:
        for f in self._state.damage_floats:
            surf = self._font_dmg.render(f.text, True, f.color)
            surf.set_alpha(f.alpha)
            screen.blit(surf, (f.x, f.y))

    # ── Float position helpers ────────────────────────────────

    def _combatant_float_pos(self, combatant: Combatant) -> tuple[int, int]:
        """Return screen position for a damage float above the combatant."""
        if combatant.is_enemy:
            n = len(self._state.enemies)
            idx = self._state.enemies.index(combatant)
            offsets = ENEMY_LAYOUTS.get(n, ENEMY_LAYOUTS[1])
            ox, oy = offsets[idx]
            cx = Settings.SCREEN_WIDTH // 2 + ox
            cy = ENEMY_AREA_H // 2 + 10 + oy
            w, h = self._enemy_rect_size(combatant)
            return cx - 15, cy - h // 2 - 30
        else:
            idx = self._state.party.index(combatant)
            row_y = ENEMY_AREA_H + 8 + idx * (ROW_H + 2)
            return PARTY_W - 60, row_y + 5
