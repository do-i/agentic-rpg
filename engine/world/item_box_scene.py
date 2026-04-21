# engine/world/item_box_scene.py

from __future__ import annotations

import pygame

from engine.common.font_provider import get_fonts
from engine.common.scene.scene import Scene
from engine.item.item_catalog import ItemCatalog
from engine.world.item_box import ItemBox

MODAL_W = 520
ROW_H = 30
TITLE_H = 42
HINT_H = 32
PAD = 20

_MC_SIZE_LABEL = {
    "mc_xs": "Magic Core (XS)",
    "mc_s":  "Magic Core (S)",
    "mc_m":  "Magic Core (M)",
    "mc_l":  "Magic Core (L)",
    "mc_xl": "Magic Core (XL)",
}


class ItemBoxScene(Scene):
    """
    Overlay scene — shows the contents of an ItemBox.
    Enter confirms: caller loots + marks opened via on_confirm callback.
    No cancel path.
    """

    def __init__(
        self,
        box: ItemBox,
        item_catalog: ItemCatalog | None,
        on_confirm: callable,
        sfx_manager=None,
    ) -> None:
        self._box = box
        self._catalog = item_catalog
        self._on_confirm = on_confirm
        self._sfx_manager = sfx_manager
        self._fonts_ready = False
        self._lines = self._build_lines()

    def _build_lines(self) -> list[str]:
        lines: list[str] = []
        for item_id, qty in self._box.loot_items:
            name = self._name_for(item_id)
            lines.append(f"{name} ×{qty}")
        for mc_id, qty in self._box.loot_magic_cores:
            name = self._name_for(mc_id) or _MC_SIZE_LABEL.get(mc_id, mc_id)
            lines.append(f"{name} ×{qty}")
        if not lines:
            lines.append("(empty)")
        return lines

    def _name_for(self, item_id: str) -> str:
        if self._catalog is not None:
            defn = self._catalog.get(item_id)
            if defn is not None:
                return defn.name
        return item_id.replace("_", " ").title()

    def _init_fonts(self) -> None:
        f = get_fonts()
        self._font_title = f.get(24, bold=True)
        self._font_row   = f.get(20)
        self._font_hint  = f.get(16)
        self._fonts_ready = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self._sfx_manager:
                    self._sfx_manager.play("confirm")
                self._on_confirm(self._box)
                return

    def update(self, delta: float) -> None:
        pass

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        body_h = TITLE_H + ROW_H * len(self._lines) + HINT_H + PAD * 2
        mw, mh = MODAL_W, body_h
        mx = (screen.get_width() - mw) // 2
        my = (screen.get_height() - mh) // 2

        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (20, 20, 45),    (mx, my, mw, mh))
        pygame.draw.rect(screen, (160, 160, 100), (mx, my, mw, mh), 2)

        title = self._font_title.render("You found:", True, (240, 220, 140))
        screen.blit(title, (mx + PAD, my + PAD))

        y = my + PAD + TITLE_H
        for line in self._lines:
            surf = self._font_row.render(line, True, (220, 220, 180))
            screen.blit(surf, (mx + PAD + 8, y))
            y += ROW_H

        hint = self._font_hint.render("ENTER  take", True, (160, 160, 120))
        screen.blit(hint, (mx + mw - hint.get_width() - PAD, my + mh - HINT_H))
