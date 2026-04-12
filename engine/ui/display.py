# engine/ui/display.py

import pygame


class Display:
    def __init__(
        self,
        screen_width: int = 1280,
        screen_height: int = 766,
        window_title: str = "",
    ) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode(
            (screen_width, screen_height),
            pygame.SCALED | pygame.RESIZABLE
        )
        pygame.display.set_caption(window_title)

    @property
    def screen(self) -> pygame.Surface:
        return self._screen

    def flip(self) -> None:
        pygame.display.flip()

    def quit(self) -> None:
        pygame.quit()
