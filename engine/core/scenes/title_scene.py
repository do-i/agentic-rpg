# engine/core/scenes/title_scene.py

import pygame
from engine.core.scene import Scene
from engine.core.settings import Settings


class TitleScene(Scene):
    def __init__(self, manifest: dict) -> None:
        self._title = manifest.get("name", "RPG")
        self._font = pygame.font.SysFont("Arial", 48)

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                pass  # NewGameScene will plug in here

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((10, 10, 30))
        text = self._font.render(self._title, True, (220, 220, 180))
        x = (Settings.SCREEN_WIDTH - text.get_width()) // 2
        y = (Settings.SCREEN_HEIGHT - text.get_height()) // 2
        screen.blit(text, (x, y))