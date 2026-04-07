# engine/scenes/scene.py

import pygame

# owns scene switching, nothing else. Scenes are the building blocks:
# WorldMap, Town, Battle, Menu etc. will all be scenes later.#
# First, the base Scene class every scene inherits this class.
class Scene:
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass

    def update(self, delta: float) -> None:
        pass

    def render(self, screen: pygame.Surface) -> None:
        pass