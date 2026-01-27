"""
Projectile entity - arrows, bolts, and other fired projectiles.
"""
import math
from .base import Entity


class Projectile(Entity):
    """
    A projectile that travels in a straight line at a given angle.
    Collides with solid tiles and entities, applying damage on hit.
    """

    def __init__(self, x, y, angle, speed, damage, owner=None):
        super().__init__(x, y, tags=["projectile"])
        self.solid = False
        self.uses_sub_grid = True

        # Movement
        self.angle = angle
        self.speed = speed
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        # Combat
        self.damage = damage
        self.damage_type = "physical"
        self.owner = owner

        # Lifetime
        self.alive = True
        self.distance_traveled = 0.0
        self.max_range = 15.0  # tiles

        # Hitbox size (in tiles)
        self.hitbox_size = 0.25

        # Visual
        self.color = (200, 180, 120)  # Arrow color

    def update(self, dt):
        """Move the projectile along its trajectory."""
        if not self.alive:
            return

        dx = self.vx * dt
        dy = self.vy * dt

        self.x += dx
        self.y += dy
        self.distance_traveled += math.sqrt(dx * dx + dy * dy)

        # Check max range
        if self.distance_traveled >= self.max_range:
            self.alive = False

    def check_tile_collision(self, world):
        """Check if the projectile hit a solid tile or went out of bounds."""
        if not self.alive:
            return False

        # Out of bounds
        if self.x < 0 or self.y < 0 or self.x >= world.width or self.y >= world.height:
            self.alive = False
            return True

        # Solid tile check
        if world.is_blocked_subgrid(self.x, self.y):
            self.alive = False
            return True

        return False

    def check_entity_collision(self, world):
        """
        Check if the projectile hit any entity.
        Returns the hit entity or None.
        """
        if not self.alive:
            return None

        half = self.hitbox_size / 2.0
        entities = world.get_entities_in_rect(
            self.x - half, self.y - half,
            self.hitbox_size, self.hitbox_size
        )

        for entity in entities:
            # Skip self, owner, other projectiles, effects
            if entity.id == self.id:
                continue
            if self.owner and entity.id == self.owner.id:
                continue
            if entity.has_tag("projectile"):
                continue
            if entity.has_tag("effect"):
                continue
            if entity.has_tag("rune_stone"):
                continue

            # Must be something hittable (actor or solid world object)
            if hasattr(entity, 'stats') or (hasattr(entity, 'solid') and entity.solid):
                return entity

        return None

    def apply_damage(self, entity):
        """Apply projectile damage to the hit entity."""
        if not self.alive:
            return

        # Actors (enemies, NPCs)
        if hasattr(entity, 'stats'):
            actual = entity.stats.take_damage(self.damage, self.damage_type)
            if actual > 0:
                print(f"[Projectile] Hit {entity} for {actual} damage")

        # World objects with slashing/damage support
        elif hasattr(entity, 'on_slashing_attack'):
            result = entity.on_slashing_attack(
                1,  # slashing power tier 1 for arrows
                self.damage,
                {"attacker": self.owner}
            )
            if result.get("affected"):
                for msg in result.get("messages", []):
                    print(f"[Projectile] {msg}")

        self.alive = False

    def should_be_removed(self):
        """Check if this projectile should be removed from the world."""
        return not self.alive
