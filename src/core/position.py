"""
Sub-grid position utilities for smooth movement.

The position system uses float coordinates in large-tile units:
- 5.0 = tile 5, sub-tile 0
- 5.375 = tile 5, sub-tile 3 (0.375 * 8 = 3)
- 5.875 = tile 5, sub-tile 7

Sub-grid: 8x8 sub-tiles per large tile (4 pixels per sub-tile)
"""
import math
from .settings import Settings


class SubGridPosition:
    """
    Helper class for sub-grid position math.

    Positions are stored as floats in large-tile units.
    Sub-tile = 1/8 of a large tile = 4 pixels.
    """

    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    @classmethod
    def from_tile(cls, tile_x, tile_y, sub_x=0, sub_y=0):
        """Create position from tile and sub-tile coordinates."""
        x = tile_x + sub_x / Settings.SUB_GRID_DIVISIONS
        y = tile_y + sub_y / Settings.SUB_GRID_DIVISIONS
        return cls(x, y)

    def get_tile(self):
        """Get the large tile coordinates (integer)."""
        return (int(math.floor(self.x)), int(math.floor(self.y)))

    def get_tile_x(self):
        """Get the large tile X coordinate."""
        return int(math.floor(self.x))

    def get_tile_y(self):
        """Get the large tile Y coordinate."""
        return int(math.floor(self.y))

    def get_sub_tile(self):
        """Get the sub-tile coordinates within the current large tile (0-7, 0-7)."""
        tile_x, tile_y = self.get_tile()
        sub_x = int((self.x - tile_x) * Settings.SUB_GRID_DIVISIONS)
        sub_y = int((self.y - tile_y) * Settings.SUB_GRID_DIVISIONS)
        # Clamp to valid range
        sub_x = max(0, min(Settings.SUB_GRID_DIVISIONS - 1, sub_x))
        sub_y = max(0, min(Settings.SUB_GRID_DIVISIONS - 1, sub_y))
        return (sub_x, sub_y)

    def get_pixel_position(self):
        """Get the pixel position for rendering."""
        pixel_x = self.x * Settings.TILE_SIZE
        pixel_y = self.y * Settings.TILE_SIZE
        return (pixel_x, pixel_y)

    def get_pixel_offset(self):
        """Get pixel offset within the current tile (for rendering)."""
        tile_x, tile_y = self.get_tile()
        offset_x = (self.x - tile_x) * Settings.TILE_SIZE
        offset_y = (self.y - tile_y) * Settings.TILE_SIZE
        return (offset_x, offset_y)

    def get_tiles_occupied(self, width=1.0, height=1.0):
        """
        Get all large tiles that an entity at this position would occupy.

        Args:
            width: Entity width in tile units (default 1.0 = 1 tile)
            height: Entity height in tile units (default 1.0 = 1 tile)

        Returns:
            List of (tile_x, tile_y) tuples
        """
        tiles = set()

        # Calculate bounds
        left = self.x
        right = self.x + width
        top = self.y
        bottom = self.y + height

        # Get all tiles in the bounding box
        min_tile_x = int(math.floor(left))
        max_tile_x = int(math.floor(right - 0.001))  # Exclude exact right edge
        min_tile_y = int(math.floor(top))
        max_tile_y = int(math.floor(bottom - 0.001))  # Exclude exact bottom edge

        for ty in range(min_tile_y, max_tile_y + 1):
            for tx in range(min_tile_x, max_tile_x + 1):
                tiles.add((tx, ty))

        return list(tiles)

    def overlaps_tile(self, tile_x, tile_y, width=1.0, height=1.0):
        """
        Check if an entity at this position overlaps a large tile.

        Args:
            tile_x, tile_y: The large tile to check
            width, height: Entity dimensions in tile units

        Returns:
            True if any overlap
        """
        # Entity bounds
        left = self.x
        right = self.x + width
        top = self.y
        bottom = self.y + height

        # Tile bounds
        tile_left = tile_x
        tile_right = tile_x + 1
        tile_top = tile_y
        tile_bottom = tile_y + 1

        # Check overlap (AABB collision)
        return (left < tile_right and right > tile_left and
                top < tile_bottom and bottom > tile_top)

    def distance_to(self, other):
        """Calculate Euclidean distance to another position."""
        if isinstance(other, SubGridPosition):
            dx = self.x - other.x
            dy = self.y - other.y
        else:
            # Assume tuple or similar with x, y attributes
            dx = self.x - other[0]
            dy = self.y - other[1]
        return math.sqrt(dx * dx + dy * dy)

    def manhattan_distance_to(self, other):
        """Calculate Manhattan distance to another position."""
        if isinstance(other, SubGridPosition):
            return abs(self.x - other.x) + abs(self.y - other.y)
        return abs(self.x - other[0]) + abs(self.y - other[1])

    def move(self, dx, dy):
        """Move position by delta (in tile units)."""
        self.x += dx
        self.y += dy

    def move_sub_tiles(self, sub_dx, sub_dy):
        """Move position by sub-tile deltas (1 sub-tile = 1/8 tile)."""
        self.x += sub_dx / Settings.SUB_GRID_DIVISIONS
        self.y += sub_dy / Settings.SUB_GRID_DIVISIONS

    def copy(self):
        """Create a copy of this position."""
        return SubGridPosition(self.x, self.y)

    def set(self, x, y):
        """Set position directly."""
        self.x = float(x)
        self.y = float(y)

    def __repr__(self):
        tile_x, tile_y = self.get_tile()
        sub_x, sub_y = self.get_sub_tile()
        return f"SubGridPosition({self.x:.3f}, {self.y:.3f}) [tile=({tile_x},{tile_y}), sub=({sub_x},{sub_y})]"

    def __eq__(self, other):
        if isinstance(other, SubGridPosition):
            return abs(self.x - other.x) < 0.0001 and abs(self.y - other.y) < 0.0001
        return False


def tile_to_sub_grid(tile_x, tile_y):
    """Convert large tile coordinates to sub-grid position (top-left of tile)."""
    return SubGridPosition(float(tile_x), float(tile_y))


def get_sub_tile_movement():
    """Get the movement amount for one sub-tile (1/8 of a tile)."""
    return 1.0 / Settings.SUB_GRID_DIVISIONS
