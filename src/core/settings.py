"""
Game settings and configuration constants.
"""

class Settings:
    # Display
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 60
    TITLE = "Magic Game"

    # Grid and tiles
    TILE_SIZE = 32
    GRID_WIDTH = 50
    GRID_HEIGHT = 50

    # Player
    PLAYER_SPEED = 4  # tiles per second

    # Colors (placeholder visuals)
    COLOR_BG = (20, 25, 30)
    COLOR_GRID = (40, 45, 50)
    COLOR_PLAYER = (100, 200, 255)
    COLOR_TREE = (50, 120, 50)
    COLOR_ROCK = (100, 100, 110)
    COLOR_WATER = (40, 80, 200)
    COLOR_WALL = (80, 70, 60)
    COLOR_GRASS = (35, 80, 35)

    # Debug
    DEBUG_MODE = True
    SHOW_GRID = True
