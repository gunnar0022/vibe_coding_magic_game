"""
Asset management system with placeholder support.

The AssetManager loads sprites, fonts, and audio from the assets folder.
When assets don't exist, it generates procedural placeholders so the game
can run without any actual asset files.
"""
import os
import pygame
import math
from ..core.settings import Settings


class AssetManager:
    """
    Centralized asset loading and placeholder generation.

    Usage:
        assets = AssetManager()
        assets.initialize()

        # Get a sprite (returns placeholder if file doesn't exist)
        sprite = assets.get_sprite("objects/tree")

        # Get with specific size
        sprite = assets.get_sprite("weapons/sword", size=(32, 32))
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.assets_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
        self.sprites = {}
        self.fonts = {}
        self.sounds = {}
        self.tile_size = Settings.TILE_SIZE
        self._initialized = True

    def initialize(self):
        """Initialize pygame modules needed for assets."""
        pygame.font.init()
        # pygame.mixer.init()  # Uncomment when adding audio

    def get_sprite(self, name, size=None):
        """
        Get a sprite by name. Loads from file or generates placeholder.

        Args:
            name: Sprite path relative to assets/sprites/ (without extension)
            size: Optional (width, height) tuple. Defaults to tile_size.

        Returns:
            pygame.Surface
        """
        size = size or (self.tile_size, self.tile_size)
        cache_key = f"{name}_{size[0]}x{size[1]}"

        if cache_key in self.sprites:
            return self.sprites[cache_key]

        # Try to load from file
        sprite = self._load_sprite_file(name, size)

        if sprite is None:
            # Generate placeholder
            sprite = self._generate_placeholder(name, size)

        self.sprites[cache_key] = sprite
        return sprite

    def _load_sprite_file(self, name, size):
        """Attempt to load a sprite from file."""
        filepath = os.path.join(self.assets_path, "sprites", f"{name}.png")

        if os.path.exists(filepath):
            try:
                sprite = pygame.image.load(filepath).convert_alpha()
                if sprite.get_size() != size:
                    sprite = pygame.transform.scale(sprite, size)
                return sprite
            except pygame.error:
                pass
        return None

    def _generate_placeholder(self, name, size):
        """Generate a procedural placeholder sprite."""
        surface = pygame.Surface(size, pygame.SRCALPHA)
        w, h = size
        padding = 2

        # Determine what kind of placeholder based on name
        name_lower = name.lower()

        if "player" in name_lower:
            return self._placeholder_player(surface, w, h, padding)
        elif "tree" in name_lower:
            return self._placeholder_tree(surface, w, h, padding, "burning" in name_lower)
        elif "rock" in name_lower:
            return self._placeholder_rock(surface, w, h, padding)
        elif "log" in name_lower:
            return self._placeholder_log(surface, w, h, padding)
        elif "bush" in name_lower:
            return self._placeholder_bush(surface, w, h, padding)
        elif "npc" in name_lower:
            return self._placeholder_npc(surface, w, h, padding)
        elif "rune_stone" in name_lower:
            return self._placeholder_rune_stone(surface, w, h, padding, "dormant" in name_lower)
        elif "sword" in name_lower:
            return self._placeholder_weapon(surface, w, h, "sword")
        elif "axe" in name_lower:
            return self._placeholder_weapon(surface, w, h, "axe")
        elif "swing" in name_lower or "slash" in name_lower:
            return self._placeholder_swing_effect(surface, w, h)
        elif "fire" in name_lower:
            return self._placeholder_effect(surface, w, h, (255, 100, 0))
        elif "water" in name_lower:
            return self._placeholder_effect(surface, w, h, (50, 150, 255))
        elif "force" in name_lower:
            return self._placeholder_effect(surface, w, h, (200, 200, 255))
        else:
            # Default placeholder - colored rectangle with X
            return self._placeholder_default(surface, w, h, name)

    def _placeholder_player(self, surface, w, h, padding):
        """Blue circle with direction indicator."""
        center = (w // 2, h // 2)
        radius = min(w, h) // 2 - padding
        pygame.draw.circle(surface, (100, 200, 255), center, radius)
        # Direction indicator (white dot at top)
        pygame.draw.circle(surface, (255, 255, 255), (center[0], center[1] - radius + 5), 3)
        return surface

    def _placeholder_tree(self, surface, w, h, padding, burning=False):
        """Green triangle tree shape."""
        color = (255, 100, 0) if burning else (50, 120, 50)
        points = [
            (w // 2, padding),
            (padding, h - padding),
            (w - padding, h - padding)
        ]
        pygame.draw.polygon(surface, color, points)
        if burning:
            # Add flame particles
            pygame.draw.circle(surface, (255, 200, 0), (w // 2, h // 4), 4)
            pygame.draw.circle(surface, (255, 150, 0), (w // 2 - 4, h // 4 + 3), 3)
        return surface

    def _placeholder_rock(self, surface, w, h, padding):
        """Gray rounded rectangle."""
        rect = pygame.Rect(padding * 2, padding * 2, w - padding * 4, h - padding * 4)
        pygame.draw.rect(surface, (100, 100, 110), rect, border_radius=6)
        return surface

    def _placeholder_log(self, surface, w, h, padding):
        """Brown horizontal rectangle for log."""
        # Main log body
        log_height = h // 3
        log_y = (h - log_height) // 2
        rect = pygame.Rect(padding, log_y, w - padding * 2, log_height)
        pygame.draw.rect(surface, (139, 90, 43), rect, border_radius=4)
        # End circles
        pygame.draw.circle(surface, (120, 75, 35), (padding + 4, h // 2), log_height // 2 - 2)
        pygame.draw.circle(surface, (120, 75, 35), (w - padding - 4, h // 2), log_height // 2 - 2)
        return surface

    def _placeholder_bush(self, surface, w, h, padding):
        """Small green circle."""
        center = (w // 2, h // 2)
        radius = min(w, h) // 3
        pygame.draw.circle(surface, (40, 100, 40), center, radius)
        return surface

    def _placeholder_npc(self, surface, w, h, padding):
        """Diamond shape for NPCs."""
        center_x, center_y = w // 2, h // 2
        half = min(w, h) // 2 - padding
        points = [
            (center_x, center_y - half),
            (center_x + half, center_y),
            (center_x, center_y + half),
            (center_x - half, center_y),
        ]
        pygame.draw.polygon(surface, (180, 160, 140), points)
        # Inner highlight
        inner_half = half - 4
        inner_points = [
            (center_x, center_y - inner_half),
            (center_x + inner_half, center_y),
            (center_x, center_y + inner_half),
            (center_x - inner_half, center_y),
        ]
        pygame.draw.polygon(surface, (220, 200, 180), inner_points)
        return surface

    def _placeholder_rune_stone(self, surface, w, h, padding, dormant=False):
        """Octagon with glow effect."""
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 2 - padding

        color = (80, 80, 90) if dormant else (120, 100, 180)

        points = []
        for i in range(8):
            angle = math.pi / 8 + i * math.pi / 4
            px = center_x + int(radius * math.cos(angle))
            py = center_y + int(radius * math.sin(angle))
            points.append((px, py))
        pygame.draw.polygon(surface, color, points)

        # Inner glow if active
        if not dormant:
            inner_radius = radius - 6
            inner_points = []
            for i in range(8):
                angle = math.pi / 8 + i * math.pi / 4
                px = center_x + int(inner_radius * math.cos(angle))
                py = center_y + int(inner_radius * math.sin(angle))
                inner_points.append((px, py))
            glow_color = (180, 160, 240)
            pygame.draw.polygon(surface, glow_color, inner_points)

        return surface

    def _placeholder_weapon(self, surface, w, h, weapon_type):
        """Simple weapon shape."""
        center_x, center_y = w // 2, h // 2

        if "sword" in weapon_type:
            # Blade
            blade_color = (180, 180, 200)
            pygame.draw.rect(surface, blade_color,
                           (center_x - 2, 4, 4, h - 12))
            # Handle
            pygame.draw.rect(surface, (100, 70, 40),
                           (center_x - 4, h - 10, 8, 8))
            # Crossguard
            pygame.draw.rect(surface, (150, 140, 100),
                           (center_x - 8, h - 14, 16, 4))
        else:  # axe
            # Handle
            pygame.draw.rect(surface, (100, 70, 40),
                           (center_x - 2, 8, 4, h - 12))
            # Blade (axe head)
            points = [
                (center_x - 2, 6),
                (center_x + 10, 12),
                (center_x + 10, 20),
                (center_x - 2, 16),
            ]
            pygame.draw.polygon(surface, (120, 100, 80), points)

        return surface

    def _placeholder_swing_effect(self, surface, w, h):
        """Arc effect for weapon swings."""
        # Draw a semi-transparent arc
        center = (w // 2, h)
        pygame.draw.arc(surface, (255, 200, 100, 180),
                       (0, 0, w, h * 2),
                       math.pi * 0.2, math.pi * 0.8, 4)
        return surface

    def _placeholder_effect(self, surface, w, h, color):
        """Generic spell effect - glowing circle."""
        center = (w // 2, h // 2)
        radius = min(w, h) // 2 - 2

        # Outer glow
        glow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, color + (100,), center, radius)
        surface.blit(glow_surf, (0, 0))

        # Inner bright core
        pygame.draw.circle(surface, color + (200,), center, radius // 2)

        return surface

    def _placeholder_default(self, surface, w, h, name):
        """Default placeholder with magenta X pattern."""
        # Magenta background (classic missing texture color)
        surface.fill((255, 0, 255, 128))

        # Draw X
        pygame.draw.line(surface, (0, 0, 0), (0, 0), (w, h), 2)
        pygame.draw.line(surface, (0, 0, 0), (w, 0), (0, h), 2)

        return surface

    def get_font(self, name="default", size=24):
        """Get a font, loading from file or using system default."""
        cache_key = f"{name}_{size}"

        if cache_key in self.fonts:
            return self.fonts[cache_key]

        font = None

        if name != "default":
            filepath = os.path.join(self.assets_path, "fonts", f"{name}.ttf")
            if os.path.exists(filepath):
                try:
                    font = pygame.font.Font(filepath, size)
                except pygame.error:
                    pass

        if font is None:
            font = pygame.font.Font(None, size)

        self.fonts[cache_key] = font
        return font

    def get_tile_sprite(self, tile_type):
        """Get a tile sprite."""
        return self.get_sprite(f"tiles/{tile_type}")

    def get_entity_sprite(self, entity_type, state="idle"):
        """Get an entity sprite with optional state."""
        # Try with state first
        sprite = self._load_sprite_file(f"objects/{entity_type}_{state}",
                                        (self.tile_size, self.tile_size))
        if sprite:
            return sprite

        # Fall back to base sprite
        return self.get_sprite(f"objects/{entity_type}")

    def get_weapon_sprite(self, weapon_type):
        """Get a weapon sprite."""
        return self.get_sprite(f"weapons/{weapon_type}")

    def get_effect_sprite(self, effect_type, size=None):
        """Get an effect sprite."""
        size = size or (self.tile_size, self.tile_size)
        return self.get_sprite(f"effects/{effect_type}", size)


# Global instance accessor
_asset_manager = None

def get_asset_manager():
    """Get the global AssetManager instance."""
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager()
    return _asset_manager
