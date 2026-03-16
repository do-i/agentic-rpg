# engine/core/container.py

from dependency_injector import containers, providers
from engine.core.display import Display
from engine.core.frame_clock import FrameClock
from engine.core.game import Game


class Container(containers.DeclarativeContainer):
    display = providers.Singleton(Display)
    clock = providers.Singleton(FrameClock)
    game = providers.Singleton(
        Game,
        display=display,
        clock=clock,
    )