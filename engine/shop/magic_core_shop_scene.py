# engine/scenes/magic_core_shop_scene.py
#
# Phase 6 — Shop + Apothecary

from __future__ import annotations

import pygame
from engine.common.scene.scene import Scene
from engine.common.scene.scene_manager import SceneManager
from engine.common.scene.scene_registry import SceneRegistry
from engine.common.game_state_holder import GameStateHolder
from engine.common.service.repository_state import RepositoryState

# Confirm dialog threshold — rates at or above this trigger confirmation
LARGE_RATE_THRESHOLD = 1_000

# ── Colors ────────────────────────────────────────────────────
C_BG          = (18, 18, 35)
C_HEADER      = (212, 200, 138)
C_TEXT        = (238, 238, 238)
C_MUTED       = (130, 130, 140)
C_DIM         = (80, 80, 90)
C_SEL_BG      = (45, 42, 75)
C_SEL_BDR     = (180, 160, 255)
C_NORM_BDR    = (55, 55, 78)
C_ROW_BG      = (28, 28, 50)
C_GP          = (200, 185, 100)
C_GP_GAIN     = (100, 220, 100)
C_DIVIDER     = (50, 50, 70)
C_HINT        = (100, 100, 115)
C_CONFIRM_BG  = (28, 14, 14)
C_CONFIRM_BDR = (180, 70, 70)
C_CONFIRM_TXT = (220, 180, 180)

# ── Layout ────────────────────────────────────────────────────
PAD        = 28
HEADER_H   = 48
ROW_H      = 52
ROW_GAP    = 4
MODAL_W    = 560
FOOTER_H   = 32

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 10


class MagicCoreShopScene(Scene):
    """
    Lets the player exchange Magic Cores for GP.

    States:
      list     — browsing available MC sizes
      qty      — selecting quantity for chosen size
      confirm  — confirmation dialog for L / XL (if enabled)
      toast    — brief "Exchanged!" message before auto-close
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        mc_sizes: list[tuple[str, str, int]],
        confirm_large: bool = True,
        return_scene_name: str = "world_map",
        sfx_manager=None,
    ) -> None:
        self._holder       = holder
        self._scene_manager = scene_manager
        self._registry     = registry
        self._on_close     = on_close
        self._mc_sizes     = mc_sizes
        self._confirm_large = confirm_large
        self._return_scene_name = return_scene_name
        self._sfx_manager  = sfx_manager

        self._state        = "list"   # list | qty | confirm | popup
        self._list_sel     = 0        # index into _available()
        self._qty          = 1
        self._popup_text   = ""
        self._fonts_ready  = False

    # ── Font init ─────────────────────────────────────────────

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 24, bold=True)
        self._font_row    = pygame.font.SysFont("Arial", 18)
        self._font_gp     = pygame.font.SysFont("Arial", 18)
        self._font_qty    = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_arrow  = pygame.font.SysFont("Arial", 22)
        self._font_hint   = pygame.font.SysFont("Arial", 15)
        self._font_toast  = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_confirm = pygame.font.SysFont("Arial", 17)
        self._fonts_ready = True

    # ── Data helpers ──────────────────────────────────────────

    def _repo(self) -> RepositoryState:
        return self._holder.get().repository

    def _available(self) -> list[tuple[str, str, int, int]]:
        """Returns list of (item_id, label, rate, qty) for owned MC sizes."""
        repo = self._repo()
        result = []
        for item_id, label, rate in self._mc_sizes:
            entry = repo.get_item(item_id)
            if entry and entry.qty > 0:
                result.append((item_id, label, rate, entry.qty))
        return result

    def _selected(self) -> tuple[str, str, int, int] | None:
        avail = self._available()
        if not avail:
            return None
        idx = min(self._list_sel, len(avail) - 1)
        return avail[idx]

    def _clamp_list_sel(self) -> None:
        avail = self._available()
        if avail:
            self._list_sel = max(0, min(self._list_sel, len(avail) - 1))

    def _qty_loop(self, delta: int, max_qty: int) -> None:
        """Adjust quantity with looping."""
        self._qty += delta
        if self._qty < 1:
            self._qty = max_qty
        elif self._qty > max_qty:
            self._qty = 1

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "popup":
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    avail = self._available()
                    if avail:
                        self._state = "list"
                    else:
                        self._on_close()
                return
            if self._state == "list":
                self._handle_list(event.key)
            elif self._state == "qty":
                self._handle_qty(event.key)
            elif self._state == "confirm":
                self._handle_confirm(event.key)

    def _handle_list(self, key: int) -> None:
        avail = self._available()
        if not avail:
            if key == pygame.K_ESCAPE:
                if self._sfx_manager:
                    self._sfx_manager.play("cancel")
                self._on_close()
            return

        if key == pygame.K_UP:
            old = self._list_sel
            self._list_sel = (self._list_sel - 1) % len(avail)
            if self._list_sel != old and self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_DOWN:
            old = self._list_sel
            self._list_sel = (self._list_sel + 1) % len(avail)
            if self._list_sel != old and self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self._sfx_manager:
                self._sfx_manager.play("confirm")
            self._qty = 1
            self._state = "qty"
        elif key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._on_close()

    def _handle_qty(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = "list"
            return
        _, _, _, max_qty = sel

        if key == pygame.K_ESCAPE:
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._state = "list"
        elif key == pygame.K_LEFT:
            self._qty_loop(-QTY_STEP_SMALL, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_RIGHT:
            self._qty_loop(QTY_STEP_SMALL, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_UP:
            self._qty_loop(-QTY_STEP_LARGE, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key == pygame.K_DOWN:
            self._qty_loop(QTY_STEP_LARGE, max_qty)
            if self._sfx_manager:
                self._sfx_manager.play("hover")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            _, _, rate, _ = sel
            if self._confirm_large and rate >= LARGE_RATE_THRESHOLD:
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._state = "confirm"
            else:
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._do_exchange()

    def _handle_confirm(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_y):
            if self._sfx_manager:
                self._sfx_manager.play("confirm")
            self._do_exchange()
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            if self._sfx_manager:
                self._sfx_manager.play("cancel")
            self._state = "qty"

    # ── Exchange ──────────────────────────────────────────────

    def _do_exchange(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id, label, rate, max_qty = sel
        qty   = min(self._qty, max_qty)
        total = qty * rate

        repo = self._repo()
        entry = repo.get_item(item_id)
        if entry is None or entry.qty < qty:
            return

        repo.remove_item(item_id, qty)
        repo.add_gp(total)

        self._popup_text  = f"Exchanged {qty} × {label}  →  +{total:,} GP"
        self._state       = "popup"
        self._clamp_list_sel()

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        # dim world underneath
        overlay = pygame.Surface(
            (screen.get_width(), screen.get_height()), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        mw = MODAL_W
        avail  = self._available()
        rows   = max(len(avail), 1)
        body_h = rows * (ROW_H + ROW_GAP) + 12
        mh     = HEADER_H + body_h + FOOTER_H + PAD * 2

        mx = (screen.get_width()  - mw) // 2
        my = (screen.get_height() - mh) // 2

        pygame.draw.rect(screen, C_BG,     (mx, my, mw, mh), border_radius=8)
        pygame.draw.rect(screen, C_SEL_BDR,(mx, my, mw, mh), 1, border_radius=8)

        self._draw_header(screen, mx, my, mw)
        self._draw_list(screen, mx, my + HEADER_H + PAD, mw, avail)
        self._draw_footer(screen, mx, my + mh - FOOTER_H - 4, mw)

        if self._state == "qty":
            self._draw_qty_overlay(screen, mx, my, mw, mh)
        elif self._state == "confirm":
            self._draw_confirm_overlay(screen)
        elif self._state == "popup":
            self._draw_popup(screen)

    def _draw_header(self, screen: pygame.Surface, mx: int, my: int, mw: int) -> None:
        title = self._font_title.render("Magic Core Exchange", True, C_HEADER)
        screen.blit(title, (mx + PAD, my + PAD // 2 + 4))

        repo = self._repo()
        gp_s = self._font_gp.render(f"GP  {repo.gp:,}", True, C_GP)
        screen.blit(gp_s, (mx + mw - gp_s.get_width() - PAD, my + PAD // 2 + 6))

        pygame.draw.line(screen, C_DIVIDER,
                         (mx + 10, my + HEADER_H),
                         (mx + mw - 10, my + HEADER_H))

    def _draw_list(self, screen: pygame.Surface,
                   mx: int, y: int, mw: int,
                   avail: list) -> None:
        if not avail:
            empty = self._font_hint.render(
                "No Magic Cores in inventory.", True, C_DIM)
            screen.blit(empty, (mx + PAD, y + 16))
            return

        for i, (item_id, label, rate, qty) in enumerate(avail):
            sel   = (i == self._list_sel) and self._state == "list"
            row_y = y + i * (ROW_H + ROW_GAP)
            rx    = mx + 10
            rw    = mw - 20

            bg  = C_SEL_BG   if sel else C_ROW_BG
            bdr = C_SEL_BDR  if sel else C_NORM_BDR
            pygame.draw.rect(screen, bg,  (rx, row_y, rw, ROW_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (rx, row_y, rw, ROW_H), 1, border_radius=4)

            if sel:
                cur = self._font_row.render("▶", True, C_HEADER)
                screen.blit(cur, (rx + 8, row_y + (ROW_H - cur.get_height()) // 2))

            # label + qty
            lbl = self._font_row.render(label, True, C_TEXT if sel else C_MUTED)
            screen.blit(lbl, (rx + 28, row_y + 8))

            qty_s = self._font_row.render(f"×  {qty}", True, C_HEADER)
            screen.blit(qty_s, (rx + 28, row_y + ROW_H - qty_s.get_height() - 8))

            # rate + total
            rate_s = self._font_row.render(
                f"{rate:,} GP each    →    {qty * rate:,} GP total",
                True, C_GP_GAIN if sel else C_GP)
            screen.blit(rate_s, (rx + rw - rate_s.get_width() - 16,
                                  row_y + (ROW_H - rate_s.get_height()) // 2))

    def _draw_footer(self, screen: pygame.Surface, mx: int, y: int, mw: int) -> None:
        pygame.draw.line(screen, C_DIVIDER, (mx + 10, y), (mx + mw - 10, y))
        hint = self._font_hint.render(
            "↑↓ select · ENTER exchange · ESC close", True, C_HINT)
        screen.blit(hint, (mx + PAD, y + 8))

    # ── Qty overlay ───────────────────────────────────────────

    def _draw_qty_overlay(self, screen: pygame.Surface,
                          mx: int, my: int, mw: int, mh: int) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id, label, rate, max_qty = sel
        total = self._qty * rate

        ow, oh = mw - 40, 140
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        pygame.draw.rect(screen, (22, 22, 44), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR,    (ox, oy, ow, oh), 2, border_radius=6)

        lbl = self._font_row.render(label, True, C_HEADER)
        screen.blit(lbl, (ox + 20, oy + 14))

        # quantity selector — arrows use non-bold font for glyph compatibility
        left_s  = self._font_arrow.render("◀", True, C_TEXT)
        num_s   = self._font_qty.render(f"  {self._qty}  ", True, C_TEXT)
        right_s = self._font_arrow.render("▶", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 44
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        max_s = self._font_hint.render(f"max {max_qty}", True, C_DIM)
        screen.blit(max_s, (ox + ow - max_s.get_width() - 16, oy + 52))

        total_s = self._font_gp.render(f"→  {total:,} GP", True, C_GP_GAIN)
        screen.blit(total_s, (ox + 20, oy + 95))

        hint = self._font_hint.render(
            "← / → qty ±1    ↑ / ↓ qty ±10    ENTER confirm    ESC back",
            True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, oy + oh - 22))

    # ── Confirm overlay ───────────────────────────────────────

    def _draw_confirm_overlay(self, screen: pygame.Surface) -> None:
        sel = self._selected()
        if not sel:
            return
        _, label, rate, _ = sel
        total = self._qty * rate

        ow, oh = 480, 110
        ox = (screen.get_width()  - ow) // 2
        oy = (screen.get_height() - oh) // 2

        pygame.draw.rect(screen, C_CONFIRM_BG,  (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_CONFIRM_BDR, (ox, oy, ow, oh), 2, border_radius=6)

        msg = self._font_confirm.render(
            f"Exchange {self._qty} × {label} for {total:,} GP?",
            True, C_CONFIRM_TXT)
        screen.blit(msg, (ox + 20, oy + 20))

        hint = self._font_hint.render(
            "ENTER / Y — Confirm    ESC / N — Cancel", True, C_HINT)
        screen.blit(hint, (ox + 20, oy + 64))

    # ── Popup ─────────────────────────────────────────────────

    def _draw_popup(self, screen: pygame.Surface) -> None:
        pw, ph = 460, 80
        px = (screen.get_width()  - pw) // 2
        py = (screen.get_height() - ph) // 2
        pygame.draw.rect(screen, C_BG,      (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR, (px, py, pw, ph), 2, border_radius=6)
        msg = self._font_toast.render(self._popup_text, True, C_GP_GAIN)
        screen.blit(msg, (px + (pw - msg.get_width()) // 2, py + 14))
        hint = self._font_hint.render("ENTER / ESC  close", True, C_HINT)
        screen.blit(hint, (px + (pw - hint.get_width()) // 2, py + ph - 28))