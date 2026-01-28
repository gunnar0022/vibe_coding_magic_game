"""
Actor entity - base for all living entities (player, NPCs, monsters).
"""
import math
from .base import Entity
from ..components import StatsComponent, StatusComponent, InventoryComponent, InteractionComponent, TransformComponent
from ..core.settings import Settings

# Diagonal movement normalization factor (1/√2)
DIAGONAL_FACTOR = 1.0 / math.sqrt(2)  # ≈ 0.707


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

        # Movement state - sub-grid movement (1/8 tile per tick)
        self.move_cooldown = 0
        self.move_speed = 0.025  # seconds between sub-tile moves (faster for smooth feel)
        self.sub_tile_step = 1.0 / Settings.SUB_GRID_DIVISIONS  # 0.125 tiles per move

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
        """Check if actor can move (not stunned/frozen, cooldown ready)."""
        if self.status.has_flag("stunned"):
            return False
        if self.status.has_flag("frozen"):
            return False
        if self.move_cooldown > 0:
            return False
        return True

    def try_move(self, dx, dy, world):
        """
        Attempt to move in direction using sub-grid movement.
        Moves by 1/8 tile (one sub-tile) per call.
        Features:
        - Diagonal movement is normalized to same speed as cardinal
        - Wall sliding: if blocked diagonally, try moving along one axis
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

        # Calculate sub-tile movement amount
        move_dx = self.sub_tile_step if dx > 0 else (-self.sub_tile_step if dx < 0 else 0)
        move_dy = self.sub_tile_step if dy > 0 else (-self.sub_tile_step if dy < 0 else 0)

        # Normalize diagonal movement so total distance is same as cardinal
        if move_dx != 0 and move_dy != 0:
            move_dx *= DIAGONAL_FACTOR
            move_dy *= DIAGONAL_FACTOR

        # Calculate target position
        new_x = self.x + move_dx
        new_y = self.y + move_dy

        # Try movement with wall sliding
        # Priority: full move > X-only slide > Y-only slide > blocked
        final_x, final_y = self.x, self.y
        moved = False

        if not world.is_blocked_subgrid(new_x, new_y):
            # Full move is clear
            final_x, final_y = new_x, new_y
            moved = True
        elif move_dx != 0 and not world.is_blocked_subgrid(new_x, self.y):
            # Y is blocked, but can slide along X
            final_x = new_x
            moved = True
        elif move_dy != 0 and not world.is_blocked_subgrid(self.x, new_y):
            # X is blocked, but can slide along Y
            final_y = new_y
            moved = True

        if not moved:
            return False

        # Execute move
        self.x = final_x
        self.y = final_y
        self.transform.set_position(final_x, final_y)
        self.move_cooldown = self.move_speed

        # Apply speed modifiers
        if self.status.has_flag("slowed"):
            self.move_cooldown *= 1.5
        if self.status.has_flag("chilled"):
            self.move_cooldown *= 1.3  # Chilled slows less than slowed
        if self.status.has_flag("muddy"):
            self.move_cooldown *= 1.4  # Muddy slows movement
        if self.status.has_flag("hastened"):
            self.move_cooldown *= 0.5

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

        # Update move cooldown
        if self.move_cooldown > 0:
            self.move_cooldown -= dt

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
