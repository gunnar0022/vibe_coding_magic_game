"""
Camera system for viewport management.
"""
import pygame
from .settings import Settings


class Camera:
    def __init__(self):
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.target = None

    def set_target(self, entity):
        """Set the entity the camera should follow."""
        self.target = entity

    def update(self):
        """Update camera position to follow target (supports float positions)."""
        if self.target is None:
            return

        # Center camera on target (target position is in tile units, may be float)
        # Convert to pixel coordinates
        target_pixel_x = self.target.x * Settings.TILE_SIZE
        target_pixel_y = self.target.y * Settings.TILE_SIZE

        # Center the camera on the target's center
        self.offset_x = target_pixel_x - Settings.SCREEN_WIDTH // 2 + Settings.TILE_SIZE // 2
        self.offset_y = target_pixel_y - Settings.SCREEN_HEIGHT // 2 + Settings.TILE_SIZE // 2

    def world_to_screen(self, world_x, world_y):
        """Convert world coordinates to screen coordinates."""
        screen_x = world_x - self.offset_x
        screen_y = world_y - self.offset_y
        return screen_x, screen_y

    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates."""
        world_x = screen_x + self.offset_x
        world_y = screen_y + self.offset_y
        return world_x, world_y

    def grid_to_screen(self, grid_x, grid_y):
        """Convert grid coordinates to screen coordinates (supports float positions)."""
        world_x = grid_x * Settings.TILE_SIZE
        world_y = grid_y * Settings.TILE_SIZE
        return self.world_to_screen(world_x, world_y)

    def grid_to_screen_int(self, grid_x, grid_y):
        """Convert grid coordinates to integer screen coordinates for rendering."""
        screen_x, screen_y = self.grid_to_screen(grid_x, grid_y)
        return (int(screen_x), int(screen_y))

    def is_visible(self, world_x, world_y, width=Settings.TILE_SIZE, height=Settings.TILE_SIZE):
        """Check if a world position is visible on screen."""
        screen_x, screen_y = self.world_to_screen(world_x, world_y)
        return (screen_x + width > 0 and screen_x < Settings.SCREEN_WIDTH and
                screen_y + height > 0 and screen_y < Settings.SCREEN_HEIGHT)
