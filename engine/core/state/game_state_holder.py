# engine/core/state/game_state_holder.py

from engine.core.state.game_state import GameState


class GameStateHolder:
    """
    Mutable holder for GameState.
    Allows AppModule to register WorldMapScene factory before
    GameState is created — NameEntryScene sets value at confirm time.
    """

    def __init__(self) -> None:
        self.value: GameState | None = None

    def set(self, game_state: GameState) -> None:
        self.value = game_state

    def get(self) -> GameState:
        if self.value is None:
            raise RuntimeError("GameState not yet initialized — confirm name entry first.")
        return self.value

    def __repr__(self) -> str:
        return f"GameStateHolder(initialized={self.value is not None})"
