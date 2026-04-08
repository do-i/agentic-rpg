# engine/scenes/item_shop_scene.py

from __future__ import annotations

from pathlib import Path

import pygame

from engine.scenes.scene import Scene
from engine.scenes.scene_manager import SceneManager
from engine.scenes.scene_registry import SceneRegistry
from engine.settings import Settings
from engine.dto.game_state_holder import GameStateHolder
from engine.service.repository_state import ITEM_QTY_CAP
from engine.world.sprite_sheet import SpriteSheet, Direction

# ── Colors ────────────────────────────────────────────────────
C_BG          = (18, 18, 35)
C_BORDER      = (160, 160, 100)
C_HEADER      = (220, 220, 180)
C_TEXT        = (238, 238, 238)
C_MUTED       = (130, 130, 140)
C_DIM         = (80, 80, 90)
C_GP          = (200, 185, 100)
C_SEL_BG      = (45, 42, 75)
C_SEL_BDR     = (180, 160, 255)
C_NORM_BDR    = (55, 55, 78)
C_ROW_BG      = (28, 28, 50)
C_DIVIDER     = (50, 50, 70)
C_HINT        = (100, 100, 115)
C_WARN        = (220, 100, 80)
C_TOAST       = (100, 220, 130)
C_LOCKED      = (90, 90, 100)

# ── Layout ────────────────────────────────────────────────────
MODAL_W       = 560
PAD           = 24
HEADER_H      = 48
SPRITE_SIZE   = 64
ROW_H         = 44
ROW_GAP       = 4
FOOTER_H      = 36
VISIBLE_ROWS  = 6
TOAST_DUR     = 1.4

QTY_STEP_SMALL = 1
QTY_STEP_LARGE = 5


class ItemShopScene(Scene):
    """
    Item shop overlay.  States: list → qty → toast (loop).
    ESC closes from list state, goes back from qty state.
    """

    def __init__(
        self,
        holder: GameStateHolder,
        scene_manager: SceneManager,
        registry: SceneRegistry,
        on_close: callable,
        shop_items: list[dict],
        sprite_path: Path,
    ) -> None:
        self._holder        = holder
        self._scene_manager = scene_manager
        self._registry      = registry
        self._on_close      = on_close
        self._shop_items    = shop_items
        self._sprite_path   = sprite_path

        self._state        = "list"   # list | qty | toast
        self._list_sel     = 0
        self._scroll       = 0
        self._qty          = 1
        self._toast_timer  = 0.0
        self._toast_text   = ""
        self._fonts_ready  = False
        self._sprite_surf: pygame.Surface | None = None
        self._sprite: SpriteSheet | None = None

    # ── Init ──────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        self._font_title  = pygame.font.SysFont("Arial", 22, bold=True)
        self._font_row    = pygame.font.SysFont("Arial", 16)
        self._font_qty    = pygame.font.SysFont("Arial", 20, bold=True)
        self._font_arrow  = pygame.font.SysFont("Arial", 20)
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

    def _available(self) -> list[dict]:
        """Shop items unlocked by current flags."""
        flags = self._holder.get().flags
        result = []
        for item in self._shop_items:
            unlock = item.get("unlock_flag")
            if unlock and not flags.has_flag(unlock):
                continue
            result.append(item)
        return result

    def _selected(self) -> dict | None:
        avail = self._available()
        if not avail:
            return None
        idx = min(self._list_sel, len(avail) - 1)
        return avail[idx]

    def _owned_qty(self, item_id: str) -> int:
        entry = self._holder.get().repository.get_item(item_id)
        return entry.qty if entry else 0

    def _display_name(self, item: dict) -> str:
        return item.get("name", item["id"].replace("_", " ").title())

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self._state == "toast":
                return
            if self._state == "list":
                self._handle_list(event.key)
            elif self._state == "qty":
                self._handle_qty(event.key)

    def _handle_list(self, key: int) -> None:
        avail = self._available()
        if not avail:
            if key == pygame.K_ESCAPE:
                self._on_close()
            return

        if key == pygame.K_UP:
            self._list_sel = max(0, self._list_sel - 1)
            self._clamp_scroll()
        elif key == pygame.K_DOWN:
            self._list_sel = min(len(avail) - 1, self._list_sel + 1)
            self._clamp_scroll()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self._selected()
            if sel and sel.get("buy_price", 0) <= self._holder.get().repository.gp:
                self._qty   = 1
                self._state = "qty"
        elif key == pygame.K_ESCAPE:
            self._on_close()

    def _handle_qty(self, key: int) -> None:
        sel = self._selected()
        if not sel:
            self._state = "list"
            return
        price  = sel.get("buy_price", 0)
        owned  = self._owned_qty(sel["id"])
        max_q  = ITEM_QTY_CAP - owned
        gp     = self._holder.get().repository.gp
        if price > 0:
            max_q = min(max_q, gp // price)
        max_q = max(max_q, 1)

        if key == pygame.K_ESCAPE:
            self._state = "list"
        elif key == pygame.K_LEFT:
            self._qty = max(1, self._qty - QTY_STEP_SMALL)
        elif key == pygame.K_RIGHT:
            self._qty = min(max_q, self._qty + QTY_STEP_SMALL)
        elif key == pygame.K_UP:
            self._qty = min(max_q, self._qty + QTY_STEP_LARGE)
        elif key == pygame.K_DOWN:
            self._qty = max(1, self._qty - QTY_STEP_LARGE)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._do_buy()

    def _clamp_scroll(self) -> None:
        if self._list_sel < self._scroll:
            self._scroll = self._list_sel
        elif self._list_sel >= self._scroll + VISIBLE_ROWS:
            self._scroll = self._list_sel - VISIBLE_ROWS + 1

    # ── Buy ───────────────────────────────────────────────────

    def _do_buy(self) -> None:
        sel = self._selected()
        if not sel:
            return
        item_id = sel["id"]
        price   = sel.get("buy_price", 0)
        total   = price * self._qty
        repo    = self._holder.get().repository

        if total > 0 and not repo.spend_gp(total):
            return  # not enough GP

        repo.add_item(item_id, self._qty)
        # apply tags from shop data
        entry = repo.get_item(item_id)
        if entry:
            for tag in sel.get("tags", []):
                entry.tags.add(tag)

        name = self._display_name(sel)
        self._toast_text  = f"Bought {self._qty} x {name}"
        self._toast_timer = TOAST_DUR
        self._state       = "toast"

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._state == "toast":
            self._toast_timer -= delta
            if self._toast_timer <= 0:
                self._state = "list"

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()
        if self._sprite_surf is None and self._sprite is None:
            self._init_sprite()

        avail   = self._available()
        rows    = min(len(avail), VISIBLE_ROWS) if avail else 1
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
        self._draw_list(screen, mx, my + HEADER_H + PAD, avail)
        self._draw_footer(screen, mx, my + mh - FOOTER_H - 4)

        if self._state == "qty":
            self._draw_qty_overlay(screen, mx, my, mh)
        elif self._state == "toast":
            self._draw_toast(screen)

    def _draw_header(self, screen: pygame.Surface, mx: int, my: int) -> None:
        # sprite
        if self._sprite_surf:
            screen.blit(self._sprite_surf, (mx + PAD, my + (HEADER_H - SPRITE_SIZE) // 2))

        title = self._font_title.render("Item Shop", True, C_HEADER)
        screen.blit(title, (mx + PAD + SPRITE_SIZE + 12,
                            my + (HEADER_H - title.get_height()) // 2))

        gp = self._holder.get().repository.gp
        gp_s = self._font_row.render(f"GP  {gp:,}", True, C_GP)
        screen.blit(gp_s, (mx + MODAL_W - gp_s.get_width() - PAD,
                            my + (HEADER_H - gp_s.get_height()) // 2))

        pygame.draw.line(screen, C_DIVIDER,
                         (mx + 10, my + HEADER_H),
                         (mx + MODAL_W - 10, my + HEADER_H))

    def _draw_list(self, screen: pygame.Surface, mx: int, y: int, avail: list) -> None:
        if not avail:
            empty = self._font_hint.render("No items available.", True, C_DIM)
            screen.blit(empty, (mx + PAD, y + 16))
            return

        gp = self._holder.get().repository.gp

        for i in range(VISIBLE_ROWS):
            idx = self._scroll + i
            if idx >= len(avail):
                break
            item       = avail[idx]
            sel        = (idx == self._list_sel) and self._state == "list"
            price      = item.get("buy_price", 0)
            affordable = price <= gp
            row_y      = y + i * (ROW_H + ROW_GAP)
            rx         = mx + 10
            rw         = MODAL_W - 20

            bg  = C_SEL_BG  if sel else C_ROW_BG
            bdr = C_SEL_BDR if sel else C_NORM_BDR
            pygame.draw.rect(screen, bg,  (rx, row_y, rw, ROW_H), border_radius=4)
            pygame.draw.rect(screen, bdr, (rx, row_y, rw, ROW_H), 1, border_radius=4)

            if sel:
                cur = self._font_row.render("▶", True, C_HEADER)
                screen.blit(cur, (rx + 8, row_y + (ROW_H - cur.get_height()) // 2))

            name   = self._display_name(item)
            name_c = C_DIM if not affordable else (C_TEXT if sel else C_MUTED)
            lbl    = self._font_row.render(name, True, name_c)
            screen.blit(lbl, (rx + 28, row_y + 6))

            owned = self._owned_qty(item["id"])
            own_s = self._font_hint.render(f"owned: {owned}", True, C_DIM)
            screen.blit(own_s, (rx + 28, row_y + ROW_H - own_s.get_height() - 4))

            price_c = C_DIM if not affordable else C_GP
            price_s = self._font_row.render(f"{price:,} GP", True, price_c)
            screen.blit(price_s, (rx + rw - price_s.get_width() - 16,
                                   row_y + (ROW_H - price_s.get_height()) // 2))

        # scroll hints
        if self._scroll > 0:
            up = self._font_hint.render("▲", True, C_HINT)
            screen.blit(up, (mx + MODAL_W - 30, y - 4))
        if self._scroll + VISIBLE_ROWS < len(avail):
            bottom_y = y + VISIBLE_ROWS * (ROW_H + ROW_GAP) - 18
            dn = self._font_hint.render("▼", True, C_HINT)
            screen.blit(dn, (mx + MODAL_W - 30, bottom_y))

    def _draw_footer(self, screen: pygame.Surface, mx: int, y: int) -> None:
        pygame.draw.line(screen, C_DIVIDER, (mx + 10, y), (mx + MODAL_W - 10, y))
        hint = self._font_hint.render(
            "↑↓ select · ENTER buy · ESC close", True, C_HINT)
        screen.blit(hint, (mx + PAD, y + 8))

    # ── Qty overlay ───────────────────────────────────────────

    def _draw_qty_overlay(self, screen: pygame.Surface,
                          mx: int, my: int, mh: int) -> None:
        sel = self._selected()
        if not sel:
            return
        price = sel.get("buy_price", 0)
        total = self._qty * price
        gp    = self._holder.get().repository.gp

        ow, oh = MODAL_W - 40, 120
        ox = mx + 20
        oy = my + mh // 2 - oh // 2

        pygame.draw.rect(screen, (22, 22, 44), (ox, oy, ow, oh), border_radius=6)
        pygame.draw.rect(screen, C_SEL_BDR,    (ox, oy, ow, oh), 2, border_radius=6)

        name = self._display_name(sel)
        lbl  = self._font_row.render(name, True, C_HEADER)
        screen.blit(lbl, (ox + 20, oy + 12))

        # qty selector — arrows use non-bold font for glyph compatibility
        left_s  = self._font_arrow.render("◀", True, C_TEXT)
        num_s   = self._font_qty.render(f"  {self._qty}  ", True, C_TEXT)
        right_s = self._font_arrow.render("▶", True, C_TEXT)
        total_w = left_s.get_width() + num_s.get_width() + right_s.get_width()
        cx = ox + ow // 2 - total_w // 2
        cy = oy + 38
        screen.blit(left_s,  (cx, cy))
        screen.blit(num_s,   (cx + left_s.get_width(), cy))
        screen.blit(right_s, (cx + left_s.get_width() + num_s.get_width(), cy))

        # total price
        col = C_WARN if total > gp else C_GP
        total_s = self._font_row.render(f"Total: {total:,} GP", True, col)
        screen.blit(total_s, (ox + 20, oy + 76))

        if total > gp:
            warn = self._font_hint.render("Not enough GP", True, C_WARN)
            screen.blit(warn, (ox + ow - warn.get_width() - 20, oy + 80))

        hint = self._font_hint.render(
            "← → qty ±1    ↑ ↓ qty ±5    ENTER confirm    ESC back",
            True, C_HINT)
        screen.blit(hint, (ox + ow // 2 - hint.get_width() // 2, oy + oh - 20))

    # ── Toast ─────────────────────────────────────────────────

    def _draw_toast(self, screen: pygame.Surface) -> None:
        surf = self._font_toast.render(self._toast_text, True, C_TOAST)
        x = (Settings.SCREEN_WIDTH  - surf.get_width())  // 2
        y = (Settings.SCREEN_HEIGHT - surf.get_height()) // 2
        screen.blit(surf, (x, y))
