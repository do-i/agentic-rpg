# engine/core/scenes/dialogue_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.settings import Settings
from engine.core.dialogue.dialogue_engine import DialogueResult

# Typewriter speeds — characters revealed per second
TEXT_SPEEDS = {
    "slow":       20,
    "fast":       60,
    "very_fast":  0,   # 0 = instant
}

BOX_H = 180
BOX_MARGIN = 20
BOX_PAD = 16
PORTRAIT_SIZE = 96
TEXT_X_OFFSET = PORTRAIT_SIZE + BOX_PAD * 2


class DialogueScene(Scene):
    """
    Overlay dialogue box — does NOT replace the current scene.
    Caller renders world map underneath, then calls this render on top.

    Usage:
        dlg = DialogueScene(result, on_complete, text_speed="fast")
        # each frame: dlg.update(delta); dlg.render(screen)
    """

    def __init__(
        self,
        result: DialogueResult,
        on_complete: callable,
        text_speed: str = "fast",
    ) -> None:
        self._lines = result.lines
        self._on_complete_cb = on_complete
        self._on_complete_data = result.on_complete
        self._speed = TEXT_SPEEDS.get(text_speed, TEXT_SPEEDS["fast"])
        self._instant = (self._speed == 0)

        self._line_index = 0
        self._char_index: float = 0.0
        self._display_text = ""
        self._line_done = False
        self._fonts_ready = False

        self._advance()  # prime first line

    def _init_fonts(self) -> None:
        self._font_text    = pygame.font.SysFont("Arial", 22)
        self._font_speaker = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_hint    = pygame.font.SysFont("Arial", 16)
        self._fonts_ready  = True

    # ── State machine ─────────────────────────────────────────

    def _advance(self) -> None:
        """Move to the next line or fire completion."""
        if self._line_index >= len(self._lines):
            self._on_complete_cb(self._on_complete_data)
            return

        self._char_index = 0.0
        self._display_text = ""
        self._line_done = self._instant

        if self._instant:
            self._display_text = self._lines[self._line_index]

    def _snap_to_end(self) -> None:
        """Show full current line immediately."""
        self._display_text = self._lines[self._line_index]
        self._char_index = float(len(self._display_text))
        self._line_done = True

    # ── Events ────────────────────────────────────────────────

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key not in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                continue

            if not self._line_done:
                # skip typewriter → snap to full line
                self._snap_to_end()
            else:
                # advance to next line
                self._line_index += 1
                self._advance()

    # ── Update ────────────────────────────────────────────────

    def update(self, delta: float) -> None:
        if self._instant or self._line_done:
            return

        current_line = self._lines[self._line_index]
        self._char_index += self._speed * delta
        revealed = int(min(self._char_index, len(current_line)))
        self._display_text = current_line[:revealed]

        if revealed >= len(current_line):
            self._line_done = True

    # ── Render ────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        if not self._fonts_ready:
            self._init_fonts()

        box_y = Settings.SCREEN_HEIGHT - BOX_H - BOX_MARGIN
        box_w = Settings.SCREEN_WIDTH - BOX_MARGIN * 2

        # background
        box_surf = pygame.Surface((box_w, BOX_H), pygame.SRCALPHA)
        box_surf.fill((12, 12, 30, 220))
        screen.blit(box_surf, (BOX_MARGIN, box_y))
        pygame.draw.rect(screen, (160, 160, 100), (BOX_MARGIN, box_y, box_w, BOX_H), 2)

        # portrait placeholder (colored rect — Phase 2 sprite integration)
        pygame.draw.rect(
            screen,
            (50, 50, 80),
            (BOX_MARGIN + BOX_PAD, box_y + BOX_PAD, PORTRAIT_SIZE, PORTRAIT_SIZE),
        )
        pygame.draw.rect(
            screen,
            (120, 120, 90),
            (BOX_MARGIN + BOX_PAD, box_y + BOX_PAD, PORTRAIT_SIZE, PORTRAIT_SIZE),
            1,
        )

        # dialogue text — word-wrapped
        text_x = BOX_MARGIN + TEXT_X_OFFSET
        text_y = box_y + BOX_PAD
        text_w = box_w - TEXT_X_OFFSET - BOX_PAD
        self._render_wrapped(screen, self._display_text, text_x, text_y, text_w)

        # advance indicator
        if self._line_done and self._line_index < len(self._lines):
            indicator = self._font_hint.render("▼ SPACE / ENTER", True, (180, 180, 100))
            screen.blit(indicator, (BOX_MARGIN + box_w - indicator.get_width() - 12, box_y + BOX_H - 24))

    def _render_wrapped(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_width: int,
    ) -> None:
        """Simple word-wrap renderer."""
        words = text.split(" ")
        line = ""
        line_y = y
        line_height = self._font_text.get_height() + 4

        for word in words:
            test = (line + " " + word).strip()
            w, _ = self._font_text.size(test)
            if w > max_width and line:
                surf = self._font_text.render(line, True, (220, 220, 180))
                screen.blit(surf, (x, line_y))
                line = word
                line_y += line_height
            else:
                line = test

        if line:
            surf = self._font_text.render(line, True, (220, 220, 180))
            screen.blit(surf, (x, line_y))
