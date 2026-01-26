"""
Transform component for position and movement.
"""
from .base import Component


class TransformComponent(Component):
    """Handles position and movement on the grid."""

    def __init__(self, x=0, y=0):
        super().__init__()
        self.x = x
        self.y = y
        self.prev_x = x
        self.prev_y = y
        self.facing = "down"  # up, down, left, right

    def move(self, dx, dy):
        """Move by delta, returns True if position changed."""
        self.prev_x = self.x
        self.prev_y = self.y
        self.x += dx
        self.y += dy

        # Update facing direction
        if dx > 0:
            self.facing = "right"
        elif dx < 0:
            self.facing = "left"
        elif dy > 0:
            self.facing = "down"
        elif dy < 0:
            self.facing = "up"

        return dx != 0 or dy != 0

    def set_position(self, x, y):
        """Set absolute position."""
        self.prev_x = self.x
        self.prev_y = self.y
        self.x = x
        self.y = y

    def revert(self):
        """Revert to previous position (for collision)."""
        self.x = self.prev_x
        self.y = self.prev_y

    def serialize(self):
        return {
            "x": self.x,
            "y": self.y,
            "facing": self.facing
        }

    def deserialize(self, data):
        self.x = data.get("x", 0)
        self.y = data.get("y", 0)
        self.facing = data.get("facing", "down")
        self.prev_x = self.x
        self.prev_y = self.y
