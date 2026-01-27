"""
Effect instance entity - temporary spell effects in the world.
"""
import math
from .base import Entity


class EffectInstance(Entity):
    """
    A temporary effect object spawned by casting a spell.
    Applies spell descriptor to overlapping entities over time.
    """

    def __init__(self, x=0, y=0, spell_descriptor=None, duration=1.0, radius=0):
        super().__init__(x, y, tags=["effect"])
        self.solid = False

        # The spell this effect applies
        self.spell_descriptor = spell_descriptor or {}

        # Effect timing
        self.duration = duration
        self.elapsed = 0.0
        self.tick_interval = 0.5  # How often to apply effect
        self.last_tick = 0.0

        # Area of effect (0 = single tile)
        self.radius = radius

        # Visual
        self.color = self._get_effect_color()

        # Track affected entities this tick to avoid double-hits
        self.affected_this_tick = set()

        # Caster reference (to avoid self-damage if desired)
        self.caster = None

    def _get_effect_color(self):
        """Determine color based on spell element."""
        element = self.spell_descriptor.get("element", "none")
        colors = {
            "fire": (255, 100, 50),
            "water": (50, 150, 255),
            "earth": (139, 119, 101),
            "air": (200, 220, 255),
            "lightning": (255, 255, 100),
            "ice": (150, 220, 255),
            "nature": (50, 200, 50),
            "dark": (80, 50, 100),
            "light": (255, 255, 200),
            "none": (200, 200, 200),
        }
        return colors.get(element, (200, 200, 200))

    def get_affected_tiles(self):
        """Get all tile positions affected by this effect (integer tiles)."""
        # Use integer tile for base position
        base_x = int(math.floor(self.x))
        base_y = int(math.floor(self.y))
        tiles = [(base_x, base_y)]

        if self.radius > 0:
            for dx in range(-self.radius, self.radius + 1):
                for dy in range(-self.radius, self.radius + 1):
                    if dx == 0 and dy == 0:
                        continue
                    # Manhattan distance for now
                    if abs(dx) + abs(dy) <= self.radius:
                        tiles.append((base_x + dx, base_y + dy))

        return tiles

    def get_affected_rect(self):
        """
        Get the affected area as a precise rectangle (sub-grid aware).

        Returns (x, y, width, height) in float tile units.
        For radius=0, returns a 1x1 tile centered on effect position.
        For radius>0, expands appropriately.
        """
        # Effect hitbox is 1 tile (or more with radius)
        # Centered on the effect's precise position
        size = 1.0 + (self.radius * 2)
        half_size = size / 2.0

        rect_x = self.x - half_size + 0.5  # Center on effect position
        rect_y = self.y - half_size + 0.5
        return (rect_x, rect_y, size, size)

    def should_tick(self):
        """Check if effect should apply this frame."""
        return self.elapsed - self.last_tick >= self.tick_interval

    def tick(self, world):
        """Apply effect to all entities in range (sub-grid aware)."""
        self.affected_this_tick.clear()
        self.last_tick = self.elapsed

        # Use rect-based detection for precise sub-grid hitbox
        rect = self.get_affected_rect()
        entities = world.get_entities_in_rect(*rect)
        results = []

        for entity in entities:
            if entity.id == self.id:  # Don't affect self
                continue
            if entity.id in self.affected_this_tick:
                continue

            # Optionally skip caster
            if self.caster and entity.id == self.caster.id:
                if not self.spell_descriptor.get("affects_caster", False):
                    continue

            result = entity.on_magic_applied(self.spell_descriptor)
            if result.get("affected"):
                results.append((entity, result))
                self.affected_this_tick.add(entity.id)

        return results

    def is_expired(self):
        """Check if effect duration has ended."""
        return self.elapsed >= self.duration

    def update(self, dt):
        super().update(dt)
        self.elapsed += dt

    def serialize(self):
        data = super().serialize()
        data.update({
            "spell_descriptor": self.spell_descriptor,
            "duration": self.duration,
            "elapsed": self.elapsed,
            "radius": self.radius,
            "tick_interval": self.tick_interval,
        })
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.spell_descriptor = data.get("spell_descriptor", {})
        self.duration = data.get("duration", 1.0)
        self.elapsed = data.get("elapsed", 0.0)
        self.radius = data.get("radius", 0)
        self.tick_interval = data.get("tick_interval", 0.5)
        self.color = self._get_effect_color()
