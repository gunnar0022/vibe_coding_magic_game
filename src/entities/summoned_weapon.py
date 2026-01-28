"""
Summoned weapon entity - magical weapons created by spell casting.
"""
import math
from .base import Entity


# Weapon type definitions with stats
WEAPON_TYPES = {
    # ============================================================
    # BASE WEAPONS
    # ============================================================
    "sword": {
        "name": "Sword",
        "hands_required": 1,
        "swing_cooldown": 0.4,
        "slashing_power": 1,
        "damage": 15,
        "color": (180, 180, 200),
        "description": "A swift one-handed blade.",
    },
    "axe": {
        "name": "Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 20,
        "color": (120, 100, 80),
        "description": "A sturdy one-handed axe.",
    },
    "big_sword": {
        "name": "Great Sword",
        "hands_required": 2,
        "swing_cooldown": 0.8,
        "slashing_power": 2,
        "damage": 40,
        "color": (200, 200, 220),
        "description": "A massive two-handed blade.",
    },
    "big_axe": {
        "name": "Great Axe",
        "hands_required": 2,
        "swing_cooldown": 1.0,
        "slashing_power": 4,
        "damage": 50,
        "color": (100, 80, 60),
        "description": "A devastating two-handed axe.",
    },
    "bow": {
        "name": "Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 20,
        "color": (160, 120, 60),
        "description": "A magical bow. Fires arrows toward the mouse.",
        "ranged": True,
        "projectile_speed": 12.0,
        "mana_per_shot": 10,
        "draw_time": 1.0,
    },
    "great_bow": {
        "name": "Great Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 35,
        "color": (180, 140, 70),
        "description": "A powerful great bow. Slower draw, more damage.",
        "ranged": True,
        "projectile_speed": 15.0,
        "mana_per_shot": 15,
        "draw_time": 1.5,
        "max_range": 20.0,
    },

    # ============================================================
    # ENCHANTED SWORDS (element + 刀)
    # ============================================================
    "flame_sword": {
        "name": "Flame Sword",
        "hands_required": 1,
        "swing_cooldown": 0.4,
        "slashing_power": 1,
        "damage": 15,
        "color": (220, 100, 40),
        "description": "A blade wreathed in flame. Burns on hit.",
        "enchantment": "fire",
        "mana_per_hit": 3,
        "hit_status": [{"name": "burning", "duration": 3.0}],
    },
    "tide_sword": {
        "name": "Tide Sword",
        "hands_required": 1,
        "swing_cooldown": 0.35,
        "slashing_power": 1,
        "damage": 15,
        "color": (60, 140, 220),
        "description": "A blade flowing with water. Wets on hit.",
        "enchantment": "water",
        "mana_per_hit": 3,
        "hit_status": [{"name": "wet", "duration": 4.0}],
    },
    "stone_sword": {
        "name": "Stone Sword",
        "hands_required": 1,
        "swing_cooldown": 0.5,
        "slashing_power": 1,
        "damage": 15,
        "color": (140, 130, 110),
        "description": "A bludgeoning stone blade. Slower but sturdy.",
        "enchantment": "earth",
        "mana_per_hit": 3,
        "damage_type": "bludgeoning",
    },
    "gale_sword": {
        "name": "Gale Blade",
        "hands_required": 1,
        "swing_cooldown": 0.3,
        "slashing_power": 1,
        "damage": 15,
        "color": (170, 210, 190),
        "description": "A wind-infused blade. Fast with minor knockback.",
        "enchantment": "air",
        "mana_per_hit": 3,
        "push_force": 1,
    },
    "power_sword": {
        "name": "Power Blade",
        "hands_required": 1,
        "swing_cooldown": 0.4,
        "slashing_power": 1,
        "damage": 15,
        "color": (200, 180, 100),
        "description": "A force-enhanced blade. Pushes on hit.",
        "enchantment": "physical",
        "mana_per_hit": 3,
        "push_force": 1,
    },
    "void_sword": {
        "name": "Void Blade",
        "hands_required": 1,
        "swing_cooldown": 0.4,
        "slashing_power": 1,
        "damage": 15,
        "color": (80, 40, 120),
        "description": "A blade of emptiness. Drains life on hit.",
        "enchantment": "void",
        "mana_per_hit": 4,
        "life_drain": True,
    },
    "radiant_sword": {
        "name": "Radiant Blade",
        "hands_required": 1,
        "swing_cooldown": 0.4,
        "slashing_power": 1,
        "damage": 15,
        "color": (240, 230, 170),
        "description": "A blade of light. Cleanses negative effects on hit.",
        "enchantment": "light",
        "mana_per_hit": 3,
        "cleanses_caster": True,
    },

    # ============================================================
    # ENCHANTED AXES (element + 斧)
    # ============================================================
    "flame_axe": {
        "name": "Flame Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 20,
        "color": (200, 80, 30),
        "description": "An axe wreathed in flame. Burns on hit.",
        "enchantment": "fire",
        "mana_per_hit": 3,
        "hit_status": [{"name": "burning", "duration": 3.0}],
    },
    "tide_axe": {
        "name": "Tide Axe",
        "hands_required": 1,
        "swing_cooldown": 0.55,
        "slashing_power": 2,
        "damage": 20,
        "color": (50, 120, 200),
        "description": "An axe flowing with water. Wets on hit.",
        "enchantment": "water",
        "mana_per_hit": 3,
        "hit_status": [{"name": "wet", "duration": 4.0}],
    },
    "stone_axe": {
        "name": "Stone Axe",
        "hands_required": 1,
        "swing_cooldown": 0.7,
        "slashing_power": 2,
        "damage": 20,
        "color": (130, 120, 100),
        "description": "A bludgeoning stone axe.",
        "enchantment": "earth",
        "mana_per_hit": 3,
        "damage_type": "bludgeoning",
    },
    "gale_axe": {
        "name": "Gale Axe",
        "hands_required": 1,
        "swing_cooldown": 0.5,
        "slashing_power": 2,
        "damage": 20,
        "color": (150, 200, 180),
        "description": "A wind-infused axe. Minor knockback.",
        "enchantment": "air",
        "mana_per_hit": 3,
        "push_force": 1,
    },
    "power_axe": {
        "name": "Power Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 20,
        "color": (190, 170, 90),
        "description": "A force-enhanced axe. Pushes on hit.",
        "enchantment": "physical",
        "mana_per_hit": 3,
        "push_force": 1,
    },
    "death_axe": {
        "name": "Death Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 20,
        "color": (70, 30, 110),
        "description": "An axe of void. Drains life on hit.",
        "enchantment": "void",
        "mana_per_hit": 4,
        "life_drain": True,
    },
    "radiant_axe": {
        "name": "Radiant Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 20,
        "color": (230, 220, 160),
        "description": "An axe of light. Cleanses negative effects.",
        "enchantment": "light",
        "mana_per_hit": 3,
        "cleanses_caster": True,
    },

    # ============================================================
    # ENCHANTED BOWS (element + 弓)
    # ============================================================
    "fire_bow": {
        "name": "Fire Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 20,
        "color": (220, 100, 40),
        "description": "A bow of flame. Fire arrows burn on hit.",
        "ranged": True,
        "projectile_speed": 12.0,
        "mana_per_shot": 13,
        "draw_time": 1.2,
        "enchantment": "fire",
        "arrow_status": [{"name": "burning", "duration": 3.0}],
    },
    "water_bow": {
        "name": "Water Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 15,
        "color": (60, 140, 220),
        "description": "A bow of water. Arrows wet targets.",
        "ranged": True,
        "projectile_speed": 12.0,
        "mana_per_shot": 13,
        "draw_time": 1.0,
        "enchantment": "water",
        "arrow_status": [{"name": "wet", "duration": 4.0}],
    },
    "stone_bow": {
        "name": "Stone Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 30,
        "color": (140, 130, 110),
        "description": "A bow of stone. Slow, heavy arrows.",
        "ranged": True,
        "projectile_speed": 9.0,
        "mana_per_shot": 15,
        "draw_time": 1.4,
        "enchantment": "earth",
    },
    "wind_bow": {
        "name": "Wind Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 15,
        "color": (170, 210, 190),
        "description": "A bow of wind. Fast arrows, extended range.",
        "ranged": True,
        "projectile_speed": 16.0,
        "mana_per_shot": 10,
        "draw_time": 1.0,
        "max_range": 20.0,
        "enchantment": "air",
    },
    "power_bow": {
        "name": "Power Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 30,
        "color": (200, 180, 100),
        "description": "A bow of force. Powerful arrows with knockback.",
        "ranged": True,
        "projectile_speed": 12.0,
        "mana_per_shot": 15,
        "draw_time": 1.3,
        "enchantment": "physical",
        "arrow_knockback": True,
    },
    "void_bow": {
        "name": "Void Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 15,
        "color": (80, 40, 120),
        "description": "A bow of void. Arrows afflict decay.",
        "ranged": True,
        "projectile_speed": 12.0,
        "mana_per_shot": 15,
        "draw_time": 1.4,
        "enchantment": "void",
        "arrow_status": [{"name": "decaying", "duration": 6.0}],
    },
    "light_bow": {
        "name": "Light Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 20,
        "color": (240, 230, 170),
        "description": "A bow of light. Hitting cleanses caster.",
        "ranged": True,
        "projectile_speed": 15.0,
        "mana_per_shot": 12,
        "draw_time": 1.0,
        "enchantment": "light",
        "cleanses_caster_on_hit": True,
    },

    # ============================================================
    # ICE WEAPONS (element + 刀/斧/弓)
    # ============================================================
    "frost_sword": {
        "name": "Frost Blade",
        "hands_required": 1,
        "swing_cooldown": 0.4,
        "slashing_power": 1,
        "damage": 15,
        "color": (140, 210, 235),
        "description": "A blade of bitter frost. Chills on hit.",
        "enchantment": "ice",
        "mana_per_hit": 3,
        "hit_status": [{"name": "chilled", "duration": 3.0}],
    },
    "frost_axe": {
        "name": "Frost Axe",
        "hands_required": 1,
        "swing_cooldown": 0.6,
        "slashing_power": 2,
        "damage": 20,
        "color": (120, 190, 220),
        "description": "An axe of bitter frost. Chills on hit.",
        "enchantment": "ice",
        "mana_per_hit": 3,
        "hit_status": [{"name": "chilled", "duration": 3.0}],
    },
    "frost_bow": {
        "name": "Frost Bow",
        "hands_required": 2,
        "swing_cooldown": 0.5,
        "slashing_power": 0,
        "damage": 20,
        "color": (140, 210, 235),
        "description": "A bow of ice. Arrows chill on hit.",
        "ranged": True,
        "projectile_speed": 11.0,
        "mana_per_shot": 13,
        "draw_time": 1.1,
        "enchantment": "ice",
        "arrow_status": [{"name": "chilled", "duration": 4.0}],
    },
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

    def is_enchanted(self):
        """Check if this weapon has an elemental enchantment."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return "enchantment" in weapon_def

    def get_enchantment(self):
        """Get the enchantment element type, or None."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("enchantment")

    def get_mana_per_hit(self):
        """Get the mana cost per melee hit for enchanted weapons."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("mana_per_hit", 0)

    def get_hit_status_effects(self):
        """Get status effects applied on hit."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("hit_status", [])

    def get_arrow_status_effects(self):
        """Get status effects applied by arrows (for ranged enchanted weapons)."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("arrow_status", [])

    def get_push_force(self):
        """Get push force on hit (for force/wind enchanted weapons)."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("push_force", 0)

    def has_life_drain(self):
        """Check if weapon drains HP on hit."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("life_drain", False)

    def cleanses_caster(self):
        """Check if weapon cleanses caster's negative status on hit."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("cleanses_caster", False)

    def cleanses_caster_on_hit(self):
        """Check if ranged weapon cleanses caster when arrow hits."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("cleanses_caster_on_hit", False)

    def get_max_range(self):
        """Get max projectile range for ranged weapons."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("max_range", 15.0)

    def has_arrow_knockback(self):
        """Check if arrows have knockback effect."""
        weapon_def = WEAPON_TYPES.get(self.weapon_type, {})
        return weapon_def.get("arrow_knockback", False)

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
