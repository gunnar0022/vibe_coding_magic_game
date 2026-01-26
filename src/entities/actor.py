"""
Actor entity - base for all living entities (player, NPCs, monsters).
"""
from .base import Entity
from ..components import StatsComponent, StatusComponent, InventoryComponent, InteractionComponent, TransformComponent


class Actor(Entity):
    """Living entity with stats, status effects, and potential inventory."""

    def __init__(self, x=0, y=0, tags=None):
        super().__init__(x, y, tags)
        self.add_tag("actor")
        self.solid = True

        # Add required components for actors
        self.stats = self.add_component(StatsComponent())
        self.status = self.add_component(StatusComponent())
        self.interaction = self.add_component(InteractionComponent())
        self.transform = self.add_component(TransformComponent(x, y))

        # Movement state
        self.move_cooldown = 0
        self.move_speed = 0.15  # seconds between moves

        # Facing direction
        self.facing = "down"

        # Control source
        self.controller = None  # "player", "ai", or specific AI behavior

    def can_move(self):
        """Check if actor can move (not stunned, cooldown ready)."""
        if self.status.has_flag("stunned"):
            return False
        if self.move_cooldown > 0:
            return False
        return True

    def try_move(self, dx, dy, world):
        """
        Attempt to move in direction.
        Returns True if move succeeded.
        """
        if not self.can_move():
            return False

        # Update facing direction regardless of movement success
        if dx > 0:
            self.facing = "right"
        elif dx < 0:
            self.facing = "left"
        elif dy > 0:
            self.facing = "down"
        elif dy < 0:
            self.facing = "up"

        # Update transform component facing
        self.transform.facing = self.facing

        new_x = self.x + dx
        new_y = self.y + dy

        # Check world bounds and collision
        if world.is_blocked(new_x, new_y):
            return False

        # Execute move
        self.x = new_x
        self.y = new_y
        self.transform.set_position(new_x, new_y)
        self.move_cooldown = self.move_speed

        # Apply speed modifiers
        if self.status.has_flag("slowed"):
            self.move_cooldown *= 1.5
        if self.status.has_flag("hastened"):
            self.move_cooldown *= 0.5

        return True

    def update(self, dt):
        super().update(dt)

        # Update move cooldown
        if self.move_cooldown > 0:
            self.move_cooldown -= dt

    def on_magic_applied(self, spell_descriptor, context=None):
        """Handle magic effects on this actor."""
        result = {"affected": False, "messages": []}

        # Check invulnerability
        if self.status.has_flag("invulnerable"):
            result["messages"].append("Target is invulnerable.")
            return result

        # Apply damage if spell has damage
        if "damage" in spell_descriptor:
            damage_info = spell_descriptor["damage"]
            actual_damage = self.stats.take_damage(
                damage_info.get("amount", 0),
                damage_info.get("type", "physical")
            )
            if actual_damage > 0:
                result["affected"] = True
                result["messages"].append(f"Took {actual_damage:.0f} damage.")

        # Apply status effects
        if "status_effects" in spell_descriptor:
            for effect in spell_descriptor["status_effects"]:
                self.status.add_effect(
                    effect["name"],
                    effect.get("duration", -1),
                    effect.get("intensity", 1.0)
                )
                result["affected"] = True
                result["messages"].append(f"Afflicted with {effect['name']}.")

        return result

    def is_alive(self):
        return self.stats.is_alive()
