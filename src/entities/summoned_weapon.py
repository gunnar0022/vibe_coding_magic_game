"""
Summoned weapon entity - magical weapons created by spell casting.
"""
import math
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
    },
    "bow": {
        "name": "Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 20,
        "color": (160, 120, 60),  # Warm wood brown
        "description": "A magical bow. Fires arrows toward the mouse.",
        "ranged": True,
        "projectile_speed": 12.0,
        "mana_per_shot": 5,
        "draw_time": 1.0,
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
        Handles float positions by using the player's current tile.
        """
        import math
        tiles = []

        # Get player's integer tile position
        px = int(math.floor(player_x))
        py = int(math.floor(player_y))

        # Primary tile in front of player
        if facing == "right":
            tiles.append((px + 1, py))
            tiles.append((px + 1, py - 1))
            tiles.append((px + 1, py + 1))
        elif facing == "left":
            tiles.append((px - 1, py))
            tiles.append((px - 1, py - 1))
            tiles.append((px - 1, py + 1))
        elif facing == "up":
            tiles.append((px, py - 1))
            tiles.append((px - 1, py - 1))
            tiles.append((px + 1, py - 1))
        elif facing == "down":
            tiles.append((px, py + 1))
            tiles.append((px - 1, py + 1))
            tiles.append((px + 1, py + 1))
        else:
            # Default to down
            tiles.append((px, py + 1))

        return tiles

    def get_swing_hitbox_rects(self, player_x, player_y, facing):
        """
        Get hitbox rectangles for swing attack (sub-grid aware).

        For cardinal directions, returns a single rectangle.
        For diagonal directions, returns a single square at the corner
        with the same total area as cardinal attacks.

        Regular weapons (1H): Cardinal 1x2 = 2 sq tiles, Diagonal ~1.41x1.41
        Great weapons (2H): Cardinal 2x3 = 6 sq tiles, Diagonal ~2.45x2.45

        Args:
            player_x, player_y: Player's precise float position
            facing: Direction player is facing (8-directional)

        Returns:
            List of (x, y, width, height) tuples for hitbox rectangles
        """
        # Great weapons have larger hitboxes
        if self.is_two_handed():
            depth = 2.0
            width = 3.0
        else:
            depth = 1.0
            width = 2.0

        half_width = width / 2.0
        cx = player_x + 0.5
        cy = player_y + 0.5

        # Cardinal directions - single rectangle
        if facing == "right":
            return [(player_x + 1.0, cy - half_width, depth, width)]
        elif facing == "left":
            return [(player_x - depth, cy - half_width, depth, width)]
        elif facing == "up":
            return [(cx - half_width, player_y - depth, width, depth)]
        elif facing == "down":
            return [(cx - half_width, player_y + 1.0, width, depth)]

        # Diagonal directions - single square at the corner
        # Area matches cardinal attack (depth * width)
        # Square side = sqrt(depth * width)
        diag_size = math.sqrt(depth * width)
        half_diag = diag_size / 2.0

        # Position the square at the diagonal corner, centered
        if facing == "up_right":
            # NE corner - square centered on corner point
            corner_x = player_x + 1.0
            corner_y = player_y
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        elif facing == "up_left":
            # NW corner
            corner_x = player_x - diag_size
            corner_y = player_y
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        elif facing == "down_right":
            # SE corner
            corner_x = player_x + 1.0
            corner_y = player_y + 1.0
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        elif facing == "down_left":
            # SW corner
            corner_x = player_x - diag_size
            corner_y = player_y + 1.0
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        else:
            # Default to down
            return [(cx - half_width, player_y + 1.0, width, depth)]

    def get_swing_hitbox_rect(self, player_x, player_y, facing):
        """
        Legacy method - returns first hitbox rect for compatibility.
        Use get_swing_hitbox_rects() for full diagonal arc support.
        """
        rects = self.get_swing_hitbox_rects(player_x, player_y, facing)
        return rects[0] if rects else (player_x, player_y + 1.0, 1.0, 1.0)

    def is_ranged(self):
        """Check if this is a ranged weapon."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("ranged", False)

    def get_projectile_speed(self):
        """Get the projectile speed for ranged weapons."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("projectile_speed", 10.0)

    def get_mana_per_shot(self):
        """Get the mana cost per shot for ranged weapons."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("mana_per_shot", 5)

    def get_draw_time(self):
        """Get the draw time in seconds for ranged weapons."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("draw_time", 1.0)

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
