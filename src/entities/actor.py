"""
Actor entity - base for all living entities (player, NPCs, monsters).
"""
import math
from .base import Entity
from ..components import StatsComponent, StatusComponent, InventoryComponent, InteractionComponent, TransformComponent
from ..core.settings import Settings

class Actor(Entity):
    """Living entity with stats, status effects, and potential inventory."""

    def __init__(self, x=0, y=0, tags=None):
        super().__init__(x, y, tags)
        self.add_tag("actor")
        self.add_tag("organic")  # All actors are organic by default (Attribute.ORGANIC)
        self.solid = True
        self.uses_sub_grid = True  # Actors use sub-grid movement

        # Add required components for actors
        self.stats = self.add_component(StatsComponent())
        self.status = self.add_component(StatusComponent())
        self.interaction = self.add_component(InteractionComponent())
        self.transform = self.add_component(TransformComponent(x, y))

        # Movement state - velocity-based smooth movement
        self.move_speed = 5.0  # tiles per second (base speed)

        # Facing direction
        self.facing = "down"

        # Control source
        self.controller = None  # "player", "ai", or specific AI behavior

        # Iframe system (invincibility frames after taking a hit)
        self.iframe_timer = 0.0
        self.iframe_duration = 0.2  # seconds of invulnerability after hit

        # Knockback system
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0
        self.knockback_friction = 12.0  # velocity decay per second
        self.base_knockback_speed = 6.0  # tiles per second at multiplier 1.0

    def can_move(self):
        """Check if actor can move (not stunned/frozen)."""
        if self.status.has_flag("stunned"):
            return False
        if self.status.has_flag("frozen"):
            return False
        return True

    def try_move(self, dx, dy, world, dt=None, speed_override=None):
        """
        Attempt to move in direction using velocity-based smooth movement.

        Args:
            dx, dy: Direction vector (will be normalized internally)
            world: World instance for collision checks
            dt: Delta time in seconds. Required for smooth movement.
                If None, falls back to a single sub-tile step (legacy compat).
            speed_override: Override move_speed for this call (tiles/sec)

        Features:
        - Velocity-based: moves speed * dt * direction per frame
        - Diagonal movement is normalized to same speed as cardinal
        - Wall sliding: if blocked diagonally, try moving along one axis
        - Status effect speed modifiers applied

        Returns True if any movement occurred.
        """
        if not self.can_move():
            return False

        # Update facing direction based on intended movement (before collision)
        if dx != 0 or dy != 0:
            if abs(dx) > abs(dy):
                self.facing = "right" if dx > 0 else "left"
            elif dy != 0:
                self.facing = "down" if dy > 0 else "up"
            self.transform.facing = self.facing

        # Determine effective speed
        effective_speed = speed_override if speed_override is not None else self.move_speed

        # Apply status effect speed modifiers
        if self.status.has_flag("slowed"):
            effective_speed *= 0.67
        if self.status.has_flag("chilled"):
            effective_speed *= 0.77
        if self.status.has_flag("muddy"):
            effective_speed *= 0.71
        if self.status.has_flag("hastened"):
            effective_speed *= 2.0

        # Calculate movement distance this frame
        if dt is not None and dt > 0:
            distance = effective_speed * dt
        else:
            # Legacy fallback: single sub-tile step
            distance = 1.0 / Settings.SUB_GRID_DIVISIONS

        # Normalize direction vector
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            norm_dx = dx / length
            norm_dy = dy / length
        else:
            return False

        move_dx = norm_dx * distance
        move_dy = norm_dy * distance

        # Calculate target position
        new_x = self.x + move_dx
        new_y = self.y + move_dy

        # Try movement with wall sliding
        # Priority: full move > X-only slide > Y-only slide > blocked
        final_x, final_y = self.x, self.y
        moved = False

        if not world.is_blocked_subgrid(new_x, new_y):
            final_x, final_y = new_x, new_y
            moved = True
        elif move_dx != 0 and not world.is_blocked_subgrid(self.x + move_dx, self.y):
            final_x = self.x + move_dx
            moved = True
        elif move_dy != 0 and not world.is_blocked_subgrid(self.x, self.y + move_dy):
            final_y = self.y + move_dy
            moved = True

        if not moved:
            return False

        # Execute move
        self.x = final_x
        self.y = final_y
        self.transform.set_position(final_x, final_y)

        return True

    def take_hit(self, damage, damage_type="physical", knockback_dir=None,
                 knockback_multiplier=1.0, status_effects=None):
        """
        Handle taking a hit with iframes, knockback, and status effects.

        Args:
            damage: Amount of damage
            damage_type: Type of damage (physical, fire, etc.)
            knockback_dir: (dx, dy) normalized direction for knockback
            knockback_multiplier: Knockback strength (0.0-3.0)
            status_effects: List of status effect dicts to apply

        Returns:
            Dict with hit result info
        """
        result = {
            "blocked": False,
            "damage": 0,
            "killed": False,
        }

        # Always apply status effects, even during iframes
        if status_effects:
            for effect in status_effects:
                self.status.add_effect(
                    effect["name"],
                    duration=effect.get("duration", 3.0),
                    intensity=effect.get("intensity", 1.0),
                )

        # Check iframes
        if self.iframe_timer > 0:
            result["blocked"] = True
            return result

        # Apply damage
        actual_damage = self.stats.take_damage(damage, damage_type)
        result["damage"] = actual_damage
        result["killed"] = not self.is_alive()

        # Start iframes
        if actual_damage > 0:
            self.iframe_timer = self.iframe_duration

        # Apply knockback
        if knockback_dir and knockback_multiplier > 0 and actual_damage > 0:
            kb_speed = self.base_knockback_speed * knockback_multiplier
            self.knockback_vx = knockback_dir[0] * kb_speed
            self.knockback_vy = knockback_dir[1] * kb_speed

        return result

    def update(self, dt):
        super().update(dt)

        # Update iframe timer
        if self.iframe_timer > 0:
            self.iframe_timer -= dt

        # Update knockback velocity with friction and collision
        if self.knockback_vx != 0 or self.knockback_vy != 0:
            # Apply knockback movement
            kb_dx = self.knockback_vx * dt
            kb_dy = self.knockback_vy * dt

            # Move with collision (store old pos for grid update)
            self.x += kb_dx
            self.y += kb_dy
            self.transform.set_position(self.x, self.y)

            # Apply friction
            friction = self.knockback_friction * dt
            if abs(self.knockback_vx) < friction:
                self.knockback_vx = 0
            else:
                self.knockback_vx -= math.copysign(friction, self.knockback_vx)
            if abs(self.knockback_vy) < friction:
                self.knockback_vy = 0
            else:
                self.knockback_vy -= math.copysign(friction, self.knockback_vy)


    def on_magic_applied(self, spell_descriptor, context=None):
        """Handle magic effects on this actor."""
        from ..reactions import get_reaction_processor

        result = {"affected": False, "messages": []}

        # Check invulnerability
        if self.status.has_flag("invulnerable"):
            result["messages"].append("Target is invulnerable.")
            return result

        # Get element from spell
        element = spell_descriptor.get("element", "none")

        # Use ReactionProcessor for elemental reactions (element+attribute)
        processor = get_reaction_processor(context.get("world") if context else None)
        reaction_results = processor.process_element_applied(self, element, context)

        if reaction_results:
            result["affected"] = True
            for r in reaction_results:
                for effect in r.get("effects", []):
                    result["messages"].append(effect)

        # Apply direct damage if spell has damage (on top of reaction damage)
        damage_info = spell_descriptor.get("damage")
        if damage_info:
            actual_damage = self.stats.take_damage(
                damage_info.get("amount", 0),
                damage_info.get("type", "physical")
            )
            if actual_damage > 0:
                result["affected"] = True
                result["messages"].append(f"Took {actual_damage:.0f} damage.")

        # Apply direct status effects from spell
        status_effects = spell_descriptor.get("status_effects")
        if status_effects:
            for effect in status_effects:
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
