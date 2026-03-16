# engine/core/settings.py

class Settings:
    # Display
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    FPS: int = 60
    WINDOW_TITLE: str = "Rusted Kingdoms"

    # Tiles
    TILE_SIZE: int = 32

    # Layers
    LAYER_GROUND: int = 0
    LAYER_MID: int = 1
    LAYER_TOP: int = 2
    LAYER_UI: int = 3