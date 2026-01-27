"""
Summoned weapon entity - magical weapons created by spell casting.
"""
from .base import Entity


# Weapon type definitions with stats
WEAPON_TYPES = {
    "sword": {
        "name": "Sword",
        "hands_required": 1,
        "swing_cooldown": 0.4,  # seconds
        "slashing_power": 1,    # damage threshold tier
        "damage": 15,
        "color": (180, 180, 200),  # Silver
        "description": "A swift one-handed blade."
    },
    "axe": {
        "name": "Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 25,
        "color": (120, 100, 80),  # Bronze/brown
        "description": "A sturdy one-handed axe."
    },
    "big_sword": {
        "name": "Great Sword",
        "hands_required": 2,
        "swing_cooldown": 0.8,
        "slashing_power": 3,
        "damage": 40,
        "color": (200, 200, 220),  # Bright silver
        "description": "A massive two-handed blade."
    },
    "big_axe": {
        "name": "Great Axe",
        "hands_required": 2,
        "swing_cooldown": 1.0,
        "slashing_power": 4,
        "damage": 50,
        "color": (100, 80, 60),  # Dark bronze
        "description": "A devastating two-handed axe."
    }
}


class SummonedWeapon(Entity):
    """
    A magical weapon summoned by the player.

    Weapons:
    - Occupy one or two hands
    - Have swing cooldowns
    - Deal slashing damage with a power threshold
    - Only one can exist at a time per player
    """

    def __init__(self, weapon_type, owner=None):
        super().__init__(tags=["summoned_weapon", "weapon"])
        self.solid = False  # Weapons don't block movement

        # Get weapon stats from definition
        weapon_def = WEAPON_TYPES.get(weapon_type, WEAPON_TYPES["sword"])

        self.weapon_type = weapon_type
        self.name = weapon_def["name"]
        self.hands_required = weapon_def["hands_required"]
        self.swing_cooldown = weapon_def["swing_cooldown"]
        self.slashing_power = weapon_def["slashing_power"]
        self.damage = weapon_def["damage"]
        self.color = weapon_def["color"]
        self.description = weapon_def["description"]

        # Current cooldown timer
        self.current_cooldown = 0.0

        # Owner reference (the player holding this weapon)
        self.owner = owner

        # Whether the weapon is currently swinging (for animation)
        self.is_swinging = False
        self.swing_timer = 0.0
        self.swing_duration = 0.15  # Visual swing duration

    def can_swing(self):
        """Check if the weapon can perform a swing attack."""
        return self.current_cooldown <= 0

    def start_swing(self):
        """
        Begin a swing attack.
        Returns True if swing started, False if on cooldown.
        """
        if not self.can_swing():
            return False

        self.current_cooldown = self.swing_cooldown
        self.is_swinging = True
        self.swing_timer = self.swing_duration
        return True

    def get_swing_damage(self):
        """Get the damage dealt by this weapon's swing."""
        return self.damage

    def get_slashing_power(self):
        """Get the slashing power tier for threshold checks."""
        return self.slashing_power

    def update(self, dt):
        """Update weapon state (cooldowns, swing animation)."""
        super().update(dt)

        # Update swing cooldown
        if self.current_cooldown > 0:
            self.current_cooldown -= dt

        # Update swing animation
        if self.is_swinging:
            self.swing_timer -= dt
            if self.swing_timer <= 0:
                self.is_swinging = False

    def get_swing_hitbox_tiles(self, player_x, player_y, facing):
        """
        Get the tiles affected by a swing attack.
        Returns a list of (x, y) tile coordinates.

        The swing is an arc in front of the player.
        """
        tiles = []

        # Primary tile in front of player
        if facing == "right":
            tiles.append((player_x + 1, player_y))
            tiles.append((player_x + 1, player_y - 1))
            tiles.append((player_x + 1, player_y + 1))
        elif facing == "left":
            tiles.append((player_x - 1, player_y))
            tiles.append((player_x - 1, player_y - 1))
            tiles.append((player_x - 1, player_y + 1))
        elif facing == "up":
            tiles.append((player_x, player_y - 1))
            tiles.append((player_x - 1, player_y - 1))
            tiles.append((player_x + 1, player_y - 1))
        elif facing == "down":
            tiles.append((player_x, player_y + 1))
            tiles.append((player_x - 1, player_y + 1))
            tiles.append((player_x + 1, player_y + 1))
        else:
            # Default to down
            tiles.append((player_x, player_y + 1))

        return tiles

    def is_one_handed(self):
        """Check if this is a one-handed weapon."""
        return self.hands_required == 1

    def is_two_handed(self):
        """Check if this is a two-handed weapon."""
        return self.hands_required >= 2

    def serialize(self):
        """Serialize weapon state (weapons don't persist between saves)."""
        return {
            "weapon_type": self.weapon_type,
            "current_cooldown": self.current_cooldown
        }

    def __repr__(self):
        return f"SummonedWeapon({self.name}, hands={self.hands_required})"
