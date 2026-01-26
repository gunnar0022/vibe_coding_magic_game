"""
Tile definition for the world grid.
"""


class Tile:
    """A single tile in the world grid."""

    def __init__(self, tile_type="ground", walkable=True):
        self.tile_type = tile_type
        self.walkable = walkable

        # Apply defaults based on type
        defaults = TILE_DEFAULTS.get(tile_type, {})
        self.color = defaults.get("color", (50, 50, 50))
        self.walkable = defaults.get("walkable", walkable)


TILE_DEFAULTS = {
    "ground": {
        "color": (45, 55, 45),
        "walkable": True,
    },
    "grass": {
        "color": (35, 70, 35),
        "walkable": True,
    },
    "dirt": {
        "color": (80, 60, 40),
        "walkable": True,
    },
    "stone": {
        "color": (90, 90, 95),
        "walkable": True,
    },
    "water_shallow": {
        "color": (40, 80, 180),
        "walkable": True,  # Slow movement
    },
    "water_deep": {
        "color": (20, 50, 150),
        "walkable": False,
    },
    "wall": {
        "color": (70, 65, 55),
        "walkable": False,
    },
    "void": {
        "color": (10, 10, 15),
        "walkable": False,
    },
}
