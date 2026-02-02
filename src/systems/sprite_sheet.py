"""
Sprite sheet loader — slices a PNG into individual frames.
"""
import pygame


class SpriteSheet:
    """Loads a sprite sheet image and slices it into fixed-size frames."""

    def __init__(self, path, frame_width=64, frame_height=64):
        self.image = pygame.image.load(path).convert_alpha()
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = self.image.get_width() // frame_width
        self.rows = self.image.get_height() // frame_height
        self._cache = {}

    def get_frame(self, row, col):
        """Return the Surface for a specific (row, col) cell, cached."""
        key = (row, col)
        if key not in self._cache:
            if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
                return None
            rect = pygame.Rect(
                col * self.frame_width,
                row * self.frame_height,
                self.frame_width,
                self.frame_height,
            )
            self._cache[key] = self.image.subsurface(rect).copy()
        return self._cache[key]
