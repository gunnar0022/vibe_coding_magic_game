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

    def can_move(self):
        """Check if actor can move (not stunned, cooldown ready)."""
        if self.status.has_flag("stunned"):
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
