"""
Enemy entities - hostile creatures the player can fight.
Data-driven via ENEMY_DEFS with shared AIBrain state machine.
"""
import math
from .actor import Actor
from .enemy_defs import ENEMY_DEFS
from ..ai import AIBrain
from ..combat import AttackSlot
from ..core.settings import Settings


class Enemy(Actor):
    """
    Data-driven enemy entity.

    Loads stats, AI config, attacks, and special flags from ENEMY_DEFS.
    Uses AIBrain for state machine behavior and AttackSlot for attack management.
    """

    def __init__(self, x=0, y=0, enemy_type="slime", patrol_points=None):
        super().__init__(x, y, tags=["enemy", enemy_type])
        self.enemy_type = enemy_type

        # Load definition
        self.enemy_def = ENEMY_DEFS.get(enemy_type, ENEMY_DEFS["slime"])

        # Stats from definition
        hp = self.enemy_def.get("hp", 50)
        self.stats.max_health = hp
        self.stats.health = hp
        self.stats.base_defense = 0

        # Apply resistances
        for dmg_type, value in self.enemy_def.get("resistances", {}).items():
            self.stats.resistances[dmg_type] = value

        # Visual
        self.color = self.enemy_def.get("color", (180, 50, 50))
        self.render_type = self.enemy_def.get("render_type", "default")
        self.size_multiplier = self.enemy_def.get("size_multiplier", 1.0)

        # Special flags
        self.flags = dict(self.enemy_def.get("flags", {}))

        # AI brain
        ai_config = dict(self.enemy_def.get("ai", {}))
        if patrol_points:
            ai_config["patrol_points"] = patrol_points
        self.brain = AIBrain(ai_config, self)

        # Attack slots
        self.attack_slots = []
        for attack_def in self.enemy_def.get("attacks", []):
            self.attack_slots.append(AttackSlot(attack_def))

        # Pending actions for game.py to process
        self.pending_projectile = None
        self.pending_aoe = None

        # Ignite nearby timer (for ember sprite)
        self._ignite_timer = 0.0

        # Movement speed (used for sub-grid movement)
        self.move_rate = 4.0
        self.move_timer = 0

        # AI state (readable)
        self.ai_state = "idle"

    def update(self, dt):
        """Update enemy AI, attacks, and special behaviors."""
        super().update(dt)

        # Tick attack cooldowns
        for slot in self.attack_slots:
            slot.update(dt)

        # Run AI brain (needs player reference)
        # The brain will be updated by the world update cycle
        # We store dt for the brain to use
        self._pending_dt = dt

        # Check if dead
        if not self.is_alive():
            self.on_death()

    def update_ai(self, dt, world, player):
        """Run AI brain tick. Called from game loop with player reference."""
        self.brain.update(dt, world, player)
        self.ai_state = self.brain.state

        # Ember sprite ignites nearby plants
        if self.flags.get("ignites_nearby") and self.is_alive():
            self._ignite_timer += dt
            if self._ignite_timer >= 1.0:
                self._ignite_timer -= 1.0
                self._ignite_nearby(world)

    def _ignite_nearby(self, world):
        """Ember sprite special: ignite nearby plant-tagged entities."""
        radius = self.flags.get("ignite_radius", 1.5)
        entities = world.get_entities_in_radius(int(self.x), int(self.y), int(radius) + 1)
        for entity in entities:
            if entity.id == self.id:
                continue
            if entity.has_tag("plant") or entity.has_tag("tree") or entity.has_tag("bush"):
                dist = self.euclidean_distance_to(entity)
                if dist <= radius:
                    fire_desc = {
                        "element": "fire",
                        "status_effects": [
                            {"name": "burning", "duration": 5.0, "intensity": 1.0},
                        ],
                    }
                    entity.on_magic_applied(fire_desc)

    def take_hit(self, damage, damage_type="physical", knockback_dir=None,
                 knockback_multiplier=1.0, status_effects=None, attacker=None):
        """
        Handle taking damage with damage threshold and special reactions.
        """
        # Bone shatter: skeleton archers take 1.5x physical damage
        if self.flags.get("bone_shatter") and damage_type in ("physical", "slashing"):
            damage *= 1.5

        # Damage threshold: stone guardian ignores weak hits
        threshold = self.flags.get("damage_threshold", 0)
        if threshold > 0:
            # Calculate what the actual damage would be after resistance
            resistance = self.stats.resistances.get(damage_type, 0.0)
            effective = damage * (1.0 - resistance)
            if effective < threshold:
                return {
                    "blocked": True,
                    "damage": 0,
                    "killed": False,
                    "message": "No effect!",
                }

        # Call parent take_hit
        result = super().take_hit(
            damage=damage,
            damage_type=damage_type,
            knockback_dir=knockback_dir,
            knockback_multiplier=knockback_multiplier,
            status_effects=status_effects,
        )

        return result

    def on_magic_applied(self, spell_descriptor, context=None):
        """Handle magic effects with special enemy reactions."""
        result = super().on_magic_applied(spell_descriptor, context)

        # Stone guardian: electric attacks cause extended stun
        element = spell_descriptor.get("element", "none")
        if element == "electric" and self.flags.get("electric_stun_duration"):
            stun_dur = self.flags["electric_stun_duration"]
            self.status.add_effect("stunned", duration=stun_dur, intensity=1.0)
            result["messages"].append(f"Stunned for {stun_dur}s by electricity!")

        return result

    def on_death(self):
        """Called when enemy dies."""
        self.active = False

    def should_be_removed(self):
        """Check if enemy should be removed from world."""
        return not self.active or not self.is_alive()


# Legacy subclasses kept as thin wrappers for backward compatibility
class StationaryEnemy(Enemy):
    """Legacy: stationary enemy. Now just a slime with no patrol."""
    def __init__(self, x=0, y=0):
        super().__init__(x, y, enemy_type="slime")


class PatrollingEnemy(Enemy):
    """Legacy: patrolling enemy. Now just a slime with patrol points."""
    def __init__(self, x=0, y=0, patrol_points=None):
        if patrol_points is None:
            patrol_points = [(x, y), (x + 3, y)]
        super().__init__(x, y, enemy_type="slime", patrol_points=patrol_points)


# Enemy type registry
ENEMY_TYPES = {
    "stationary": StationaryEnemy,
    "patrolling": PatrollingEnemy,
    "slime": "slime",
    "skeleton_archer": "skeleton_archer",
    "ember_sprite": "ember_sprite",
    "stone_guardian": "stone_guardian",
}


def create_enemy(enemy_type, x, y, **kwargs):
    """
    Factory function to create enemies by type.

    Args:
        enemy_type: String type name (key in ENEMY_DEFS, or legacy "stationary"/"patrolling")
        x, y: Spawn position
        **kwargs: Additional arguments (e.g., patrol_points)

    Returns:
        Enemy instance
    """
    # Legacy types
    if enemy_type == "stationary":
        return StationaryEnemy(x, y)
    elif enemy_type == "patrolling":
        return PatrollingEnemy(x, y, **kwargs)

    # Data-driven types
    if enemy_type in ENEMY_DEFS:
        return Enemy(x, y, enemy_type=enemy_type, **kwargs)

    # Fallback
    return Enemy(x, y, enemy_type="slime")
