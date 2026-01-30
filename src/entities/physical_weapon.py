"""
PhysicalWeapon - adapts an ItemInstance to the SummonedWeapon combat interface.
Game combat code works unchanged with either weapon type.
"""
import math
from .base import Entity


class PhysicalWeapon(Entity):
    """
    A physical weapon equipped from inventory.
    Implements the same interface as SummonedWeapon so game.py combat code
    works unchanged.
    """

    def __init__(self, item_instance, owner=None):
        super().__init__(tags=["physical_weapon", "weapon"])
        self.solid = False

        self.item_instance = item_instance
        self.owner = owner

        # Pull stats from item def
        self.weapon_type = item_instance.item_def_id
        self.name = item_instance.name
        self.hands_required = item_instance.hands_required
        self.swing_cooldown = item_instance.cooldown
        self.slashing_power = item_instance.slashing_power
        self.damage = item_instance.damage
        self.color = item_instance.color

        # Runtime state
        self.current_cooldown = 0.0
        self.is_swinging = False
        self.swing_timer = 0.0
        self.swing_duration = 0.15

    def can_swing(self):
        return self.current_cooldown <= 0

    def start_swing(self):
        if not self.can_swing():
            return False
        self.current_cooldown = self.swing_cooldown
        self.is_swinging = True
        self.swing_timer = self.swing_duration
        return True

    def get_swing_damage(self):
        return self.damage

    def get_slashing_power(self):
        return self.slashing_power

    def update(self, dt):
        super().update(dt)
        if self.current_cooldown > 0:
            self.current_cooldown -= dt
        if self.is_swinging:
            self.swing_timer -= dt
            if self.swing_timer <= 0:
                self.is_swinging = False

    def get_swing_hitbox_rects(self, player_x, player_y, facing):
        """Same hitbox calculation as SummonedWeapon."""
        if self.is_two_handed():
            depth = 2.0
            width = 3.0
        else:
            depth = 1.0
            width = 2.0

        half_width = width / 2.0
        cx = player_x + 0.5
        cy = player_y + 0.5

        if facing == "right":
            return [(player_x + 1.0, cy - half_width, depth, width)]
        elif facing == "left":
            return [(player_x - depth, cy - half_width, depth, width)]
        elif facing == "up":
            return [(cx - half_width, player_y - depth, width, depth)]
        elif facing == "down":
            return [(cx - half_width, player_y + 1.0, width, depth)]

        # Diagonal directions
        diag_size = math.sqrt(depth * width)
        half_diag = diag_size / 2.0

        if facing == "up_right":
            corner_x = player_x + 1.0
            corner_y = player_y
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        elif facing == "up_left":
            corner_x = player_x - diag_size
            corner_y = player_y
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        elif facing == "down_right":
            corner_x = player_x + 1.0
            corner_y = player_y + 1.0
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        elif facing == "down_left":
            corner_x = player_x - diag_size
            corner_y = player_y + 1.0
            return [(corner_x, corner_y - half_diag, diag_size, diag_size)]
        else:
            return [(cx - half_width, player_y + 1.0, width, depth)]

    def get_swing_hitbox_rect(self, player_x, player_y, facing):
        rects = self.get_swing_hitbox_rects(player_x, player_y, facing)
        return rects[0] if rects else (player_x, player_y + 1.0, 1.0, 1.0)

    def is_ranged(self):
        return False

    def is_enchanted(self):
        return False

    def get_enchantment(self):
        return None

    def get_mana_per_hit(self):
        return 0

    def get_hit_status_effects(self):
        return []

    def get_push_force(self):
        return self.item_instance.push_force

    def cleanses_caster(self):
        return False

    def get_stamina_cost(self):
        """Compute stamina cost from weapon stats: swing_cooldown * 20 * hands_required."""
        return self.swing_cooldown * 20 * self.hands_required

    def is_one_handed(self):
        return self.hands_required == 1

    def is_two_handed(self):
        return self.hands_required >= 2

    def serialize(self):
        return {
            "item_instance": self.item_instance.serialize(),
            "current_cooldown": self.current_cooldown,
        }

    def __repr__(self):
        return f"PhysicalWeapon({self.name}, hands={self.hands_required})"
