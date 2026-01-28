from .settings import Settings
from .camera import Camera
from .position import SubGridPosition, tile_to_sub_grid, get_sub_tile_movement


def __getattr__(name):
    """Lazy import for Game to avoid circular dependency."""
    if name == "Game":
        from .game import Game
        return Game
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
