# engine/core/display.py

import pygame
from engine.core.settings import Settings


class Display:
    def __init__(self) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode(
            (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT),
            pygame.SCALED | pygame.RESIZABLE
        )
        pygame.display.set_caption(Settings.WINDOW_TITLE)

    @property
    def screen(self) -> pygame.Surface:
        return self._screen

    def flip(self) -> None:
        pygame.display.flip()

    def quit(self) -> None:
        pygame.quit()