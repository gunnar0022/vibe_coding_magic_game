"""
Enemy entities - hostile creatures the player can fight.
"""
import math
from .actor import Actor
from ..core.settings import Settings


class Enemy(Actor):
    """
    Base class for enemy entities.

    Enemies:
    - Use sub-grid movement
    - Have health and can take damage
    - Update AI behavior each frame
    - Currently don't damage the player (placeholder for combat system)
    """

    def __init__(self, x=0, y=0, enemy_type="enemy"):
        super().__init__(x, y, tags=["enemy", enemy_type])
        self.enemy_type = enemy_type

        # Default enemy stats
        self.stats.max_health = 50
        self.stats.health = 50
        self.stats.base_defense = 0

        # Movement speed (sub-tiles per second)
        self.move_rate = 4.0  # How many sub-tiles per second
        self.move_timer = 0

        # Visual
        self.color = (180, 50, 50)  # Red-ish

        # AI state
        self.ai_state = "idle"

    def update(self, dt):
        """Update enemy AI and state."""
        super().update(dt)

        # Update AI behavior (override in subclasses)
        self.update_ai(dt)

        # Check if dead
        if not self.is_alive():
            self.on_death()

    def update_ai(self, dt):
        """Override in subclasses for specific AI behavior."""
        pass

    def on_death(self):
        """Called when enemy dies. Override for death effects."""
        self.active = False

    def should_be_removed(self):
        """Check if enemy should be removed from world."""
        return not self.active or not self.is_alive()

    def take_hit(self, damage, damage_type="physical", attacker=None):
        """
        Handle taking damage from an attack.

        Args:
            damage: Amount of damage
            damage_type: Type of damage (physical, fire, etc.)
            attacker: The entity that caused the damage

        Returns:
            Dict with hit result info
        """
        actual_damage = self.stats.take_damage(damage, damage_type)
        result = {
            "affected": actual_damage > 0,
            "damage": actual_damage,
            "killed": not self.is_alive()
        }
        return result


class StationaryEnemy(Enemy):
    """
    An enemy that doesn't move.
    Just exists at a position and can be hit by weapons/spells.
    """

    def __init__(self, x=0, y=0):
        super().__init__(x, y, enemy_type="stationary_enemy")

        # Stationary enemies have lower stats
        self.stats.max_health = 30
        self.stats.health = 30

        # Visual (dark red)
        self.color = (150, 40, 40)

        self.ai_state = "stationary"

    def update_ai(self, dt):
        """Stationary enemies don't do anything."""
        pass


class PatrollingEnemy(Enemy):
    """
    An enemy that patrols between two points.
    Moves smoothly on sub-grid.
    """

    def __init__(self, x=0, y=0, patrol_points=None):
        super().__init__(x, y, enemy_type="patrolling_enemy")

        # Patrol configuration
        if patrol_points is None:
            # Default: patrol 3 tiles to the right and back
            patrol_points = [(x, y), (x + 3, y)]
        self.patrol_points = patrol_points
        self.current_target_index = 1  # Start moving toward second point

        # Movement speed (tiles per second)
        self.patrol_speed = 2.0  # tiles per second

        # Visual (orange-red)
        self.color = (200, 100, 50)

        self.ai_state = "patrolling"

    def update_ai(self, dt):
        """Move toward current patrol target."""
        if not self.patrol_points or len(self.patrol_points) < 2:
            return

        # Get current target
        target = self.patrol_points[self.current_target_index]
        target_x, target_y = target

        # Calculate direction to target
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if we've reached the target
        if distance < 0.1:  # Close enough
            # Switch to next patrol point
            self.current_target_index = (self.current_target_index + 1) % len(self.patrol_points)
            return

        # Normalize direction
        if distance > 0:
            dx /= distance
            dy /= distance

        # Calculate movement amount this frame
        move_amount = self.patrol_speed * dt

        # Move toward target
        new_x = self.x + dx * move_amount
        new_y = self.y + dy * move_amount

        # Update position (no collision for simple patrol)
        self.x = new_x
        self.y = new_y
        self.transform.set_position(new_x, new_y)

        # Update facing direction
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"
        self.transform.facing = self.facing


# Enemy type registry for spawning
ENEMY_TYPES = {
    "stationary": StationaryEnemy,
    "patrolling": PatrollingEnemy,
}


def create_enemy(enemy_type, x, y, **kwargs):
    """
    Factory function to create enemies by type.

    Args:
        enemy_type: String type name ("stationary", "patrolling")
        x, y: Spawn position
        **kwargs: Additional arguments for specific enemy types

    Returns:
        Enemy instance
    """
    enemy_class = ENEMY_TYPES.get(enemy_type, StationaryEnemy)
    return enemy_class(x, y, **kwargs)
