# engine/scenes/apothecary_scene.py
#
# Apothecary overlay — crafting recipes from materials + magic cores + GP.

from __future__ import annotations

from pathlib import Path

import pygame

from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.settings import Settings
from engine.common.game_state_holder import GameStateHolder
from engine.world.sprite_sheet import SpriteSheet, Direction

# MC size label → item id mapping
_MC_SIZE_TO_ID = {"XS": "mc_xs", "S": "mc_s", "M": "mc_m", "L": "mc_l", "XL": "mc_xl"}

# ── Colors ────────────────────────────────────────────────────
C_BG          = (18, 18, 35)
C_BORDER      = (120, 160, 120)
C_HEADER      = (180, 220, 180)
C_TEXT         = (238, 238, 238)
C_MUTED        = (130, 130, 140)
C_DIM          = (80, 80, 90)
C_GP           = (200, 185, 100)
C_SEL_BG       = (35, 50, 42)
C_SEL_BDR      = (130, 200, 140)
C_NORM_BDR     = (55, 55, 78)
C_ROW_BG       = (28, 28, 50)
C_DIVIDER      = (50, 50, 70)
C_HINT         = (100, 100, 115)
C_WARN         = (220, 100, 80)
C_TOAST        = (100, 220, 130)
C_LOCKED       = (90, 90, 100)
C_READY        = (100, 200, 120)
C_MISSING      = (200, 130, 100)

# ── Layout ────────────────────────────────────────────────────
MODAL_W       = 560
PAD           = 24
HEADER_H      = 48
SPRITE_SIZE   = 64
ROW_H         = 44
ROW_GAP       = 4
FOOTER_H      = 36
VISIBLE_ROWS  = 6
POPUP_W       = 360


class ApothecaryScene(Scene):
    """
    Apothecary overlay.  States: list → detail → toast (loop).
    ESC closes from list state, goes back from detail state.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        recipes: list[dict],
        sprite_path: Path,
        sfx_manager=None,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close
        self._recipes       = recipes
        self._sprite_path   = sprite_path
        self._sfx_manager   = sfx_manager

        self._state        = "list"   # list | detail | popup
        self._list_sel     = 0
        self._scroll       = 0
        self._popup_text   = ""
        self._fonts_ready  = False
        self._sprite_surf: pygame.Surface | None = None
        self._sprite: SpriteSheet | None = None

    # ── Init ──────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_row    = pygame.font.SysFont("Arial", 16)
        self._font_detail = pygame.font.SysFont("Arial", 16)
        self._font_detail_b = pygame.font.SysFont("Arial", 16, bold=True)
        self._font_hint   = pygame.font.SysFont("Arial", 15)
        self._font_toast  = pygame.font.SysFont("Arial", 20, bold=True)
        self._fonts_ready = True

    def _init_sprite(self) -> None:
        try:
            self._sprite = SpriteSheet(self._sprite_path)
            frame = self._sprite.get_frame(Direction.DOWN, 0)
            self._sprite_surf = pygame.transform.scale(frame, (SPRITE_SIZE, SPRITE_SIZE))
        except Exception:
            self._sprite_surf = None

    # ── Data ──────────────────────────────────────────────────

    def _visible_recipes(self) -> list[dict]:
        """All recipes — both locked and unlocked — shown in list."""
        return self._recipes

    def _is_unlocked(self, recipe: dict) -> bool:
        unlock = recipe.get("unlock_flag")
        if not unlock:
            return True
        return self._holder.get().flags.has_flag(unlock)

    def _has_inputs(self, recipe: dict) -> bool:
        """Check if player has all required inputs."""
        repo = self._holder.get().repository
        inputs = recipe.get("inputs", {})
        # check items
        for req in inputs.get("items", []):
            if not repo.has_item(req["id"], req["qty"]):
                return False
        # check magic cores
        for req in inputs.get("mc", []):
            mc_id = _MC_SIZE_TO_ID.get(req["size"])
            if not mc_id or not repo.has_item(mc_id, req["qty"]):
                return False
        return True

    def _can_afford(self, recipe: dict) -> bool:
        return self._holder.get().repository.gp >= recipe.get("gp_cost", 0)

    def _can_craft(self, recipe: dict) -> bool:
        return self._is_unlocked(recipe) and self._has_inputs(recipe) and self._can_afford(recipe)

    def _selected(self) -> dict | None:
        recipes = self._visible_recipes()
        if not recipes:
            return None
        idx = min(self._list_sel, len(recipes) - 1)
        return recipes[idx]

    def _owned_qty(self, item_id: str) -> int:
        entry = self._holder.get().repository.get_item(item_id)
        return entry.qty if entry else 0

    def _item_name(self, item_id: str) -> str:
        entry = self._holder.get().repository.get_item(item_id)
        if entry and entry.name:
            return entry.name
        return item_id.replace("_", " ").title()

    def _mc_name(self, size: str) -> str:
        return f"Magic Core ({size})"

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "popup":
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._state = "list"
                return
            if self._state == "list":
                self._handle_list(event.key)
            elif self._state == "detail":
                self._handle_detail(event.key)

    def _handle_list(self, key: int) -> None:
        recipes = self._visible_recipes()
        if not recipes:
            if key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_close()
            return

        if key == pygame.K_UP:
            new = max(0, self._list_sel - 1)
            if new != self._list_sel and self._sfx_manager:
                self._sfx_manager.play("hover")
            self._list_sel = new
            self._clamp_scroll()
        elif key == pygame.K_DOWN:
            new = min(len(recipes) - 1, self._list_sel + 1)
            if new != self._list_sel and self._sfx_manager:
                self._sfx_manager.play("hover")
            self._list_sel = new
            self._clamp_scroll()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self._selected()
            if sel and self._is_unlocked(sel):
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._state = "detail"
        elif key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._on_close()

    def _handle_detail(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = "list"
            return
        if key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._state = "list"
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._can_craft(sel):
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._do_craft(sel)

    def _clamp_scroll(self) -> None:
        if self._list_sel < self._scroll:
            self._scroll = self._list_sel
        elif self._list_sel >= self._scroll + VISIBLE_ROWS:
            self._scroll = self._list_sel - VISIBLE_ROWS + 1

    # ── Craft ─────────────────────────────────────────────────

    def _do_craft(self, recipe: dict) -> None:
        repo = self._holder.get().repository
        gp_cost = recipe.get("gp_cost", 0)
        inputs = recipe.get("inputs", {})

        # consume GP
        if gp_cost > 0 and not repo.spend_gp(gp_cost):
            return

        # consume items
        for req in inputs.get("items", []):
            repo.remove_item(req["id"], req["qty"])

        # consume magic cores
        for req in inputs.get("mc", []):
            mc_id = _MC_SIZE_TO_ID.get(req["size"])
            if mc_id:
                repo.remove_item(mc_id, req["qty"])

        # produce output
        output = recipe.get("output", {})
        out_id = output.get("item")
        out_qty = output.get("qty", 1)
        if out_id:
            repo.add_item(out_id, out_qty)

        out_name = self._item_name(out_id) if out_id else "???"
        self._popup_text  = f"Crafted {out_qty} x {out_name}"
        self._state       = "popup"

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        if self._sprite_surf is None and self._sprite is None:
            self._init_sprite()

        recipes = self._visible_recipes()
        rows    = min(len(recipes), VISIBLE_ROWS) if recipes else 1
        body_h  = rows * (ROW_H + ROW_GAP) + 12
        mh      = HEADER_H + body_h + FOOTER_H + PAD * 2

        mx = (Settings.SCREEN_WIDTH  - MODAL_W) // 2
        my = (Settings.SCREEN_HEIGHT - mh) // 2

        # dim background
        overlay = pygame.Surface(
            (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # modal box
        pygame.draw.rect(screen, C_BG,     (mx, my, MODAL_W, mh), border_radius=8)
        pygame.draw.rect(screen, C_BORDER, (mx, my, MODAL_W, mh), 2, border_radius=8)

        self._draw_header(screen, mx, my)
        self._draw_list(screen, mx, my + HEADER_H + PAD, recipes)
        self._draw_footer(screen, mx, my + mh - FOOTER_H - 4)

        if self._state == "detail":
            self._draw_detail_overlay(screen, mx, my, mh)
        elif self._state == "popup":
            self._draw_popup(screen)

    def _draw_header(self, screen: pygame.Surface, mx: int, my: int) -> None:
        if self._sprite_surf:
            screen.blit(self._sprite_surf, (mx + PAD, my + (HEADER_H - SPRITE_SIZE) // 2))

        title = self._font_title.render("Apothecary", True, C_HEADER)
        screen.blit(title, (mx + PAD + SPRITE_SIZE + 12,
                            my + (HEADER_H - title.get_height()) // 2))

        gp = self._holder.get().repository.gp
        gp_s = self._font_row.render(f"GP  {gp:,}", True, C_GP)
        screen.blit(gp_s, (mx + MODAL_W - gp_s.get_width() - PAD,
                            my + (HEADER_H - gp_s.get_height()) // 2))

        pygame.draw.line(screen, C_DIVIDER,
                         (mx + 10, my + HEADER_H),
                         (mx + MODAL_W - 10, my + HEADER_H))

    def _draw_list(self, screen: pygame.Surface, mx: int, y: int,
                   recipes: list[dict]) -> None:
        if not recipes:
            empty = self._font_hint.render("No recipes available.", True, C_DIM)
            screen.blit(empty, (mx + PAD, y + 16))
            return

        for i in range(VISIBLE_ROWS):
            idx = self._scroll + i
            if idx >= len(recipes):
                break
            recipe = recipes[idx]
            sel = (idx == self._list_sel) and self._state == "list"
            unlocked = self._is_unlocked(recipe)
            ready = unlocked and self._has_inputs(recipe) and self._can_afford(recipe)
            row_y = y + i * (ROW_H + ROW_GAP)
            rx = mx + 10
            rw = MODAL_W - 20

            bg  = C_SEL_BG  if sel else C_ROW_BG
            bdr = C_SEL_BDR if sel else C_NORM_BDR
            pygame.draw.rect(screen, bg,  (rx, row_y, rw, ROW_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (rx, row_y, rw, ROW_H), 1, border_radius=4)

            if sel:
                cur = self._font_row.render("▶", True, C_HEADER)
                screen.blit(cur, (rx + 8, row_y + (ROW_H - cur.get_height()) // 2))

            # status icon
            if unlocked:
                icon = "●" if ready else "○"
                icon_c = C_READY if ready else C_MISSING
            else:
                icon = "🔒"
                icon_c = C_LOCKED
            icon_s = self._font_row.render(icon, True, icon_c)
            screen.blit(icon_s, (rx + 28, row_y + (ROW_H - icon_s.get_height()) // 2))

            # scroll name (always visible)
            scroll_name = recipe.get("scroll_name", recipe["id"])
            name_c = C_LOCKED if not unlocked else (C_TEXT if sel else C_MUTED)
            lbl = self._font_row.render(scroll_name, True, name_c)
            screen.blit(lbl, (rx + 50, row_y + 6))

            # output item name (only if unlocked)
            if unlocked:
                output = recipe.get("output", {})
                out_id = output.get("item", "")
                out_qty = output.get("qty", 1)
                out_name = self._item_name(out_id)
                sub = self._font_hint.render(
                    f"→ {out_name} ×{out_qty}", True, C_DIM)
                screen.blit(sub, (rx + 50, row_y + ROW_H - sub.get_height() - 4))
            else:
                sub = self._font_hint.render("???", True, C_LOCKED)
                screen.blit(sub, (rx + 50, row_y + ROW_H - sub.get_height() - 4))

            # GP cost (only if unlocked)
            if unlocked:
                gp_cost = recipe.get("gp_cost", 0)
                affordable = self._can_afford(recipe)
                price_c = C_DIM if not affordable else C_GP
                price_s = self._font_row.render(f"{gp_cost:,} GP", True, price_c)
                screen.blit(price_s, (rx + rw - price_s.get_width() - 16,
                                       row_y + (ROW_H - price_s.get_height()) // 2))

        # scroll hints
        if self._scroll > 0:
            up = self._font_hint.render("▲", True, C_HINT)
            screen.blit(up, (mx + MODAL_W - 30, y - 4))
        if self._scroll + VISIBLE_ROWS < len(recipes):
            bottom_y = y + VISIBLE_ROWS * (ROW_H + ROW_GAP) - 18
            dn = self._font_hint.render("▼", True, C_HINT)
            screen.blit(dn, (mx + MODAL_W - 30, bottom_y))

    def _draw_footer(self, screen: pygame.Surface, mx: int, y: int) -> None:
        pygame.draw.line(screen, C_DIVIDER, (mx + 10, y), (mx + MODAL_W - 10, y))
        hint = self._font_hint.render(
            "↑↓ select · ENTER view · ESC close", True, C_HINT)
        screen.blit(hint, (mx + PAD, y + 8))

    # ── Detail overlay ────────────────────────────────────────

    def _draw_detail_overlay(self, screen: pygame.Surface,
                             mx: int, my: int, mh: int) -> None:
        sel = self._selected()
        if not sel:
            return

        inputs = sel.get("inputs", {})
        item_inputs = inputs.get("items", [])
        mc_inputs = inputs.get("mc", [])
        input_count = len(item_inputs) + len(mc_inputs)
        gp_cost = sel.get("gp_cost", 0)
        output = sel.get("output", {})
        out_id = output.get("item", "")
        out_qty = output.get("qty", 1)
        out_name = self._item_name(out_id)

        # overlay height: output + inputs + cost + hints
        line_h = 22
        oh = 60 + input_count * line_h + 70
        ow = MODAL_W - 40
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        pygame.draw.rect(screen, (22, 22, 44), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR,    (ox, oy, ow, oh), 2, border_radius=6)

        cy = oy + 14

        # recipe name
        scroll_name = sel.get("scroll_name", sel["id"])
        lbl = self._font_detail_b.render(scroll_name, True, C_HEADER)
        screen.blit(lbl, (ox + 20, cy))
        cy += 28

        # output
        out_s = self._font_detail.render(f"Output:  {out_name} ×{out_qty}", True, C_READY)
        screen.blit(out_s, (ox + 20, cy))
        cy += 24

        # divider
        pygame.draw.line(screen, C_DIVIDER, (ox + 20, cy), (ox + ow - 20, cy))
        cy += 8

        # inputs header
        inp_lbl = self._font_detail_b.render("Inputs:", True, C_TEXT)
        screen.blit(inp_lbl, (ox + 20, cy))
        cy += line_h

        repo = self._holder.get().repository

        # item inputs
        for req in item_inputs:
            item_id = req["id"]
            req_qty = req["qty"]
            owned = self._owned_qty(item_id)
            name = self._item_name(item_id)
            has_enough = owned >= req_qty
            color = C_TEXT if has_enough else C_WARN
            txt = f"  {name}  ×{req_qty}  (owned: {owned})"
            s = self._font_detail.render(txt, True, color)
            screen.blit(s, (ox + 28, cy))
            cy += line_h

        # MC inputs
        for req in mc_inputs:
            size = req["size"]
            req_qty = req["qty"]
            mc_id = _MC_SIZE_TO_ID.get(size, "")
            owned = self._owned_qty(mc_id)
            name = self._mc_name(size)
            has_enough = owned >= req_qty
            color = C_TEXT if has_enough else C_WARN
            txt = f"  {name}  ×{req_qty}  (owned: {owned})"
            s = self._font_detail.render(txt, True, color)
            screen.blit(s, (ox + 28, cy))
            cy += line_h

        cy += 4

        # GP cost
        affordable = self._can_afford(sel)
        gp_color = C_GP if affordable else C_WARN
        gp_s = self._font_detail.render(
            f"Cost: {gp_cost:,} GP", True, gp_color)
        screen.blit(gp_s, (ox + 20, cy))

        bal = repo.gp
        bal_s = self._font_detail.render(f"Balance: {bal:,} GP", True, C_DIM)
        screen.blit(bal_s, (ox + ow - bal_s.get_width() - 20, cy))
        cy += 28

        # hint line
        can = self._can_craft(sel)
        if can:
            hint_text = "ENTER craft · ESC back"
        else:
            hint_text = "ESC back"
        hint = self._font_hint.render(hint_text, True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, cy))

    # ── Popup ─────────────────────────────────────────────────

    def _draw_popup(self, screen: pygame.Surface) -> None:
        ph = 80
        px = (Settings.SCREEN_WIDTH  - POPUP_W) // 2
        py = (Settings.SCREEN_HEIGHT - ph) // 2
        pygame.draw.rect(screen, C_BG,     (px, py, POPUP_W, ph), border_radius=6)
        pygame.draw.rect(screen, C_BORDER, (px, py, POPUP_W, ph), 2, border_radius=6)
        msg = self._font_toast.render(self._popup_text, True, C_TOAST)
        screen.blit(msg, (px + (POPUP_W - msg.get_width()) // 2, py + 14))
        hint = self._font_hint.render("ENTER / ESC  close", True, C_HINT)
        screen.blit(hint, (px + (POPUP_W - hint.get_width()) // 2, py + ph - 28))
